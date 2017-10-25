# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#
import atexit
import json
import copy
import os
import pickle
import logging
import dateutil.parser
from distutils.dir_util import mkpath
from tempfile import NamedTemporaryFile
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.base_service import BaseService
from mash.services.obs.defaults import Defaults
from mash.services.obs.build_result import OBSImageBuildResult
from mash.logging_logfile import MashLog


class OBSImageBuildResultService(BaseService):
    """
    Implements Open BuildService image result network
    service

    Attributes

    * :attr:`custom_args`
      Custom obs arguments:

      [logfile]:
          local obs logfile name, defaults to: /tmp/obs_service.log

      [job_dir]:
          Directory to create and manage OBSImageBuildResult
          watchdog jobs, defaults to: /var/tmp/obs_service/

      [download_dir]:
          Directory name passed to instances of OBSImageBuildResult
          where it is used to determine the location for image
          downloads, defaults to /tmp
    """
    def post_init(self, custom_args=None):
        if not custom_args:
            custom_args = {}

        self.logfile = custom_args['logfile'] \
            if 'logfile' in custom_args else Defaults.get_log_file()

        self.download_directory = custom_args['download_dir'] \
            if 'download_dir' in custom_args else Defaults.get_download_dir()

        self.job_directory = custom_args['job_dir'] \
            if 'job_dir' in custom_args else Defaults.get_jobs_dir()

        logging.basicConfig()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        MashLog.set_logfile(self.log, self.logfile, self.host)

        mkpath(self.job_directory)

        self.jobs = {}
        self.clients = {}
        self.last_log_result = {}

        # read and reload done jobs
        jobs_done_dir = Defaults.get_jobs_done_dir()
        for retired_job_file in os.listdir(jobs_done_dir):
            with open(jobs_done_dir + retired_job_file, 'rb') as retired:
                try:
                    job_worker = pickle.load(retired)
                    self.jobs[job_worker.job_id] = job_worker
                except Exception as e:
                    self.log.error(
                        'Could not reload {0}: {1}'.format(retired_job_file, e)
                    )

        # read and launch open jobs
        for job_file in os.listdir(self.job_directory):
            self._start_job(os.sep.join([self.job_directory, job_file]))

        self.bind_log_queue()

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self._run_control_consumer, 'date'
        )
        self.scheduler.add_job(
            self._job_listener, 'interval', max_instances=1, seconds=3
        )
        self.scheduler.add_job(
            self._log_listener, 'interval', max_instances=1, seconds=3
        )
        atexit.register(lambda: os._exit(0))
        self.scheduler.start()

    def _send_control_response(self, result, publish=False):
        message = result['message']
        if result['ok']:
            self.log.info(message)
        else:
            self.log.error(message)
        if publish:
            response = {
                'obs_control_response': result
            }
            self.log.info(self._json_message(response))

    def _run_control_consumer(self):
        self.consume_queue(
            self._control_in, self.bind_service_queue()
        )
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            if self.channel.is_open:
                self.channel.close()

    def _job_listener(self):
        for job_id, listener in list(self.clients.items()):
            job_data = listener['job'].get_image_status()
            if job_data['job_status'] == 'success':
                trigger_info = {
                    'image_source': job_data['image_source']
                }
                try:
                    self.bind_listener_queue(job_id)
                    self.publish_listener_message(
                        job_id, self._json_message(trigger_info)
                    )
                    job_info = self._delete_job(job_id)
                    self._send_control_response(job_info, publish=False)
                except Exception:
                    # failed to publish, don't dequeue
                    pass

    def _log_listener(self):
        result = {
            'obs_job_log': {}
        }
        for job_id, job in list(self.jobs.items()):
            result['obs_job_log'][job_id] = job.get_image_status()
        if self.last_log_result != result:
            self.log.info(self._json_message(result))
        self.last_log_result = copy.deepcopy(result)

    def _control_in(self, channel, method, properties, message):
        """
        On message sent by client

        The message is interpreted as json data and allows for:

        1. add new job
        2. add job to listener
        3. delete job
        """
        message_data = {}
        try:
            message_data = self._json_loads_byteified(format(message))
        except Exception as e:
            return self._send_control_response(
                {
                    'ok': False,
                    'message': 'JSON:deserialize error: {0} : {1}'.format(
                        message, e
                    )
                }, publish=True
            )
        if 'obsjob' in message_data:
            result = self._add_job(message_data)
        elif 'obsjob_listen' in message_data:
            result = self._add_to_listener(message_data['obsjob_listen'])
        elif 'obsjob_delete' in message_data and message_data['obsjob_delete']:
            result = self._delete_job(message_data['obsjob_delete'])
        else:
            result = {
                'ok': False,
                'message': 'No idea what to do with: {0}'.format(message_data)
            }
        self._send_control_response(result, publish=True)
        self.channel.basic_ack(method.delivery_tag)

    def _add_to_listener(self, job_id):
        """
        Add job to listener queue

        listen job example:
        {
            "obsjob_listen": "123"
        }
        """
        if job_id not in self.jobs:
            return {
                'ok': False,
                'message': 'Job:[{0}]: No such job'.format(job_id)
            }
        self.clients[job_id] = {
            'job': self.jobs[job_id]
        }
        return {
            'ok': True,
            'message': 'Job:[{0}]: Now in listener queue'.format(job_id)
        }

    def _add_job(self, data):
        """
        Add a new job description file and start a watchdog job

        job description example:
        {
          "obsjob": {
              "id": "123",
              "project": "Virtualization:Appliances:Images:Testing_x86",
              "image": "test-image-oem",
              "utctime": "now|always|timestring_utc_timezone",
              "conditions": [
                  {"package": ["kernel-default", ">=4.13.1", ">=1.1"]},
                  {"image": "1.42.1"}
              ]
          }
        }
        """
        job_info = self._validate_job_description(data)
        if not job_info['ok']:
            return job_info
        else:
            job_file = NamedTemporaryFile(
                prefix='job-', suffix='.json',
                dir=self.job_directory, delete=False
            )
            with open(job_file.name, 'w') as job_description:
                job_description.write(self._json_message(data))
            return self._start_job(job_file.name)

    def _delete_job(self, job_id):
        """
        Delete job description and stop watchdog job

        delete job description example:
        {
            "obsjob_delete": "123"
        }
        """
        if job_id not in self.jobs:
            return {
                'ok': False,
                'message': 'No such job id: {0}'.format(job_id)
            }
        else:
            job_worker = self.jobs[job_id]
            # delete job file
            try:
                os.remove(job_worker.job_file)
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job[{0}]: Deletion failed: {1}'.format(
                        job_id, e
                    )
                }
            else:
                # stop running job
                if job_worker:
                    job_worker.stop_watchdog()

                # delete job from job and listener queue
                del self.jobs[job_id]
                if job_id in self.clients:
                    del self.clients[job_id]
                return {
                    'ok': True,
                    'message': 'Job:[{0}]: Deleted'.format(job_id)
                }

    def _validate_job_description(self, job_data):
        if 'obsjob' not in job_data:
            return {
                'ok': False,
                'message': 'Invalid job: no obsjob'
            }
        job = job_data['obsjob']
        if 'id' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no job id'
            }
        if job['id'] in self.jobs:
            return {
                'ok': False,
                'message': 'Job:[{0}]: Already exists'.format(job['id'])
            }
        if 'image' not in job:
            return {
                'ok': False,
                'message': 'Job:[{0}]: Invalid job: no image name'.format(
                    job['id']
                )
            }
        if 'project' not in job:
            return {
                'ok': False,
                'message': 'Job:[{0}]: Invalid job: no project name'.format(
                    job['id']
                )
            }
        if 'utctime' not in job:
            return {
                'ok': False,
                'message': 'Job:[{0}]: Invalid job: no time given'.format(
                    job['id']
                )
            }
        elif job['utctime'] != 'now' and job['utctime'] != 'always':
            try:
                dateutil.parser.parse(job['utctime']).isoformat()
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job:[{0}]: Invalid time: {1}'.format(
                        job['id'], e
                    )
                }
        return {
            'ok': True,
            'message': 'OK'
        }

    def _start_job(self, job_file):
        with open(job_file) as job_description:
            job = self._json_load_byteified(job_description)['obsjob']
            if 'conditions' not in job:
                job['conditions'] = None

            job_id = job['id']
            time = job['utctime']
            nonstop = False
            if time == 'now':
                time = None
            elif time == 'always':
                time = None
                nonstop = True
            else:
                time = dateutil.parser.parse(job['utctime']).isoformat()

            job_worker = OBSImageBuildResult(
                job_id=job_id, job_file=job_file, logfile=self.logfile,
                project=job['project'], package=job['image'],
                conditions=job['conditions'],
                download_directory=self.download_directory
            )
            job_worker.start_watchdog(
                nonstop=nonstop, isotime=time
            )
            self.jobs[job_id] = job_worker
            return {
                'ok': True,
                'message': 'Job:[{0}]: Started'.format(job_id)
            }

    def _json_load_byteified(self, file_handle):
        return self._byteify(
            json.load(file_handle, object_hook=self._byteify),
            ignore_dicts=True
        )

    def _json_loads_byteified(self, json_text):
        return self._byteify(
            json.loads(json_text, object_hook=self._byteify),
            ignore_dicts=True
        )

    def _byteify(self, data, ignore_dicts=False):
        # if this is a unicode string, return its string representation
        if isinstance(data, unicode):
            return data.encode('utf-8')
        # if this is a list of values, return list of byteified values
        if isinstance(data, list):
            return [self._byteify(item, ignore_dicts=True) for item in data]
        # if this is a dictionary, return dictionary of byteified keys
        # and values but only if we haven't already byteified it
        if isinstance(data, dict) and not ignore_dicts:
            return {
                self._byteify(key, ignore_dicts=True): self._byteify(
                    value, ignore_dicts=True
                ) for key, value in data.iteritems()
            }
        # if it's anything else, return it in its original form
        return data

    def _json_message(self, data_dict):
        return json.dumps(
            data_dict, sort_keys=True, indent=4, separators=(',', ': ')
        )
