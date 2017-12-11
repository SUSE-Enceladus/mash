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
import os
import pickle
import dateutil.parser
from distutils.dir_util import mkpath
from tempfile import NamedTemporaryFile

# project
from mash.services.base_service import BaseService
from mash.services.obs.defaults import Defaults
from mash.services.obs.build_result import OBSImageBuildResult
from mash.services.obs.config import OBSConfig
from mash.utils.json_format import JsonFormat


class OBSImageBuildResultService(BaseService):
    """
    Implements Open BuildService image result network
    service
    """
    def post_init(self):
        # read config file
        config = OBSConfig()

        # setup service log file
        self.set_logfile(config.get_log_file())

        # setup service data directories
        self.download_directory = config.get_download_directory()
        self.job_directory = Defaults.get_jobs_dir()

        mkpath(self.job_directory)

        self.jobs = {}
        self.clients = {}

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

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(
            self._control_in, self.bind_service_queue()
        )
        try:
            self.channel.start_consuming(to_tuple=True)
        except Exception:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.close_connection()

    def _send_job_response(self, job_id, status_message):
        self.log.info(status_message, extra={'job_id': job_id})

    def _send_listen_response(self, job_id, trigger_info):
        if job_id in self.clients:
            try:
                self.bind_listener_queue(job_id)
                self.publish_listener_message(
                    job_id, JsonFormat.json_message(trigger_info)
                )
                del self.clients[job_id]
                self.log.info(
                    'Job deleted from listen pipeline',
                    extra={'job_id': job_id}
                )
            except Exception:
                # failed to publish, don't dequeue
                pass

    def _send_control_response(self, result, job_id=None):
        message = result['message']

        job_metadata = {}
        if job_id:
            job_metadata['job_id'] = job_id

        if result['ok']:
            self.log.info(message, extra=job_metadata)
        else:
            self.log.error(message, extra=job_metadata)

    def _control_in(self, message, channel, method, properties):
        """
        On message sent by client

        The message is interpreted as json data and allows for:

        1. add new job
        2. add job to listener
        3. delete job
        """
        channel.basic.ack(delivery_tag=method['delivery_tag'])
        message_data = {}
        job_id = None

        try:
            message_data = JsonFormat.json_loads(format(message))
        except Exception as e:
            return self._send_control_response(
                {
                    'ok': False,
                    'message': 'JSON:deserialize error: {0} : {1}'.format(
                        message, e
                    )
                }
            )
        if 'obsjob' in message_data:
            job_id = message_data['obsjob'].get('id', None)
            self.log.info(
                JsonFormat.json_message(message_data),
                extra={'job_id': job_id}
            )
            result = self._add_job(message_data)
        elif 'obsjob_listen' in message_data:
            job_id = message_data['obsjob_listen']
            self.log.info(
                'Setting Job to listen pipeline',
                extra={'job_id': job_id}
            )
            result = self._add_to_listener(job_id)
        elif 'obsjob_delete' in message_data and message_data['obsjob_delete']:
            job_id = message_data['obsjob_delete']
            self.log.info(
                'Deleting Job'.format(job_id),
                extra={'job_id': job_id}
            )
            result = self._delete_job(job_id)
        else:
            result = {
                'ok': False,
                'message': 'No idea what to do with: {0}'.format(message_data)
            }
        self._send_control_response(result, job_id)

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
                'message': 'Job does not exist, can not add to listen pipeline'
            }
        self.clients[job_id] = {
            'job': self.jobs[job_id]
        }
        self.jobs[job_id].call_result_handler()
        return {
            'ok': True,
            'message': 'Job now in listen pipeline'
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
                job_description.write(JsonFormat.json_message(data))
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
                'message': 'Job does not exist, can not delete it'
            }
        else:
            job_worker = self.jobs[job_id]
            # delete job file
            try:
                os.remove(job_worker.job_file)
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job deletion failed: {0}'.format(e)
                }
            else:
                # stop running job
                if job_worker:
                    job_worker.stop_watchdog()

                # delete obs job instance
                del self.jobs[job_id]

                # delete reference in listener queue if present
                if job_id in self.clients:
                    del self.clients[job_id]

                return {
                    'ok': True,
                    'message': 'Job Deleted'
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
                'message': 'Job already exists'
            }
        if 'image' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no image name'
            }
        if 'project' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no project name'
            }
        if 'utctime' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no time given'
            }
        elif job['utctime'] != 'now' and job['utctime'] != 'always':
            try:
                dateutil.parser.parse(job['utctime']).isoformat()
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Invalid job time: {0}'.format(e)
                }
        return {
            'ok': True,
            'message': 'OK'
        }

    def _start_job(self, job_file):
        with open(job_file) as job_description:
            job = JsonFormat.json_load(job_description)['obsjob']
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
                job_id=job_id, job_file=job_file,
                project=job['project'], package=job['image'],
                conditions=job['conditions'],
                download_directory=self.download_directory
            )
            job_worker.set_log_handler(self._send_job_response)
            job_worker.set_result_handler(self._send_listen_response)
            job_worker.start_watchdog(
                nonstop=nonstop, isotime=time
            )
            self.jobs[job_id] = job_worker
            return {
                'ok': True,
                'message': 'Job started'
            }
