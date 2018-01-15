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
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.base_service import BaseService
from mash.services.uploader.defaults import Defaults
from mash.services.uploader.upload_image import UploadImage
from mash.services.uploader.config import UploaderConfig
from mash.utils.json_format import JsonFormat


class UploadImageService(BaseService):
    """
    Implements upload to the public cloud network service
    """
    def post_init(self):
        # read config file
        config = UploaderConfig()

        # setup service log file
        self.set_logfile(config.get_log_file())

        # upload image instances
        self.jobs = {}

        # upload image instances sending information
        # to a queue for a potentially listening client
        self.clients = {}

        # read and reload done jobs
        jobs_done_dir = Defaults.get_jobs_done_dir()
        for retired_job_file in os.listdir(jobs_done_dir):
            with open(jobs_done_dir + retired_job_file, 'rb') as retired:
                try:
                    upload_image = pickle.load(retired)
                    upload_image.set_log_handler(
                        self._send_job_response
                    )
                    upload_image.set_result_handler(
                        self._send_listen_response
                    )
                    self.jobs[upload_image.job_id] = upload_image
                except Exception as e:
                    self.log.error(
                        'Could not reload {0}: {1}'.format(retired_job_file, e)
                    )

        # start job scheduler
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

        # read and launch open jobs
        self.restart_jobs(self._schedule_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(
            self._control_in, self.bind_service_queue()
        )
        try:
            self.channel.start_consuming()
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

    def _control_in(self, message):
        """
        On message sent by client

        The message is interpreted as json data and allows for:

        1. add new job
        2. add job to listener
        3. delete job
        """
        message.ack()
        job_data = {}
        job_id = None

        try:
            job_data = JsonFormat.json_loads(format(message.body))
        except Exception as e:
            return self._send_control_response(
                {
                    'ok': False,
                    'message': 'JSON:deserialize error: {0} : {1}'.format(
                        message.body, e
                    )
                }
            )
        if 'uploadjob' in job_data:
            job_id = job_data['uploadjob'].get('id', None)
            self.log.info(
                JsonFormat.json_message(job_data),
                extra={'job_id': job_id}
            )
            result = self._add_job(job_data)
        elif 'uploadjob_listen' in job_data and job_data['uploadjob_listen']:
            job_id = job_data['uploadjob_listen']
            self.log.info(
                'Setting Job to listen pipeline',
                extra={'job_id': job_id}
            )
            result = self._add_to_listener(job_id)
        elif 'uploadjob_delete' in job_data and job_data['uploadjob_delete']:
            job_id = job_data['uploadjob_delete']
            self.log.info(
                'Deleting Job'.format(job_id),
                extra={'job_id': job_id}
            )
            result = self._delete_job(job_id)
        else:
            result = {
                'ok': False,
                'message': 'No idea what to do with: {0}'.format(job_data)
            }
        if result:
            self._send_control_response(result, job_id)

    def _add_to_listener(self, job_id):
        """
        Add job to listener queue

        listen job example:
        {
            "uploadjob_listen": "123"
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
        Add a new job description file and start an image upload job

        job description example:

        {
          "uploadjob": {
            "id": "123",
            "utctime": "now|always|timestring_utc_timezone",
            "cloud_image_name": "name",
            "cloud_image_description": "description",
            "ec2": {
                "launch_ami": "ami-bc5b48d0",
                "region": "eu-central-1"
            }
          }
        }
        """
        job_info = self._validate_job_description(data)
        if not job_info['ok']:
            return job_info
        else:
            data = data['uploadjob']
            data['job_file'] = self.persist_job_config(data)
            return self._schedule_job(data)

    def _delete_job(self, job_id):
        """
        Delete job description and stop image upload job

        delete job description example:
        {
            "uploadjob_delete": "123"
        }
        """
        if job_id not in self.jobs:
            return {
                'ok': False,
                'message': 'Job does not exist, can not delete it'
            }
        else:
            upload_image = self.jobs[job_id]
            # delete job file
            try:
                os.remove(upload_image.job_file)
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job deletion failed: {0}'.format(e)
                }
            else:
                # delete upload image job instance
                self.jobs[job_id].stop()
                del self.jobs[job_id]

                # delete reference in listener queue if present
                if job_id in self.clients:
                    del self.clients[job_id]

                return {
                    'ok': True,
                    'message': 'Job Deleted'
                }

    def _validate_job_description(self, job_data):
        # validate job description. Currently only Amazon EC2 is supported
        if 'uploadjob' not in job_data:
            return {
                'ok': False,
                'message': 'Invalid job: no uploadjob'
            }
        job = job_data['uploadjob']
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
        if 'cloud_image_name' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no cloud image name'
            }
        if 'cloud_image_description' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no cloud image description'
            }
        if 'ec2' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no EC2 parameter record'
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

    def _schedule_job(self, job_description):
        job = job_description
        time = job['utctime']
        nonstop = False
        if time == 'now':
            time = None
        elif time == 'always':
            time = None
            nonstop = True
        else:
            time = dateutil.parser.parse(job['utctime']).isoformat()
        if time:
            self.scheduler.add_job(
                self._start_job, 'date', args=[job, nonstop],
                run_date=time, timezone='utc'
            )
        else:
            self.scheduler.add_job(
                self._start_job, args=[job, nonstop]
            )

    def _start_job(self, job, nonstop):
        job_id = job['id']
        csp_name = None
        csp_upload_args = None
        if 'ec2' in job:
            csp_name = 'ec2'
            csp_upload_args = job[csp_name]
        if nonstop:
            # always upload does not expect connected services to
            # provide information e.g the obs image to be available
            # at job start
            lookup_timeout_sec = None
        else:
            # now or timeboxed upload expects connected services to
            # provide the obs image and all other required data to be
            # available at job start (+10sec)
            lookup_timeout_sec = 10

        upload_image = UploadImage(
            job_id, job['job_file'], csp_name,
            job['cloud_image_name'], job['cloud_image_description'],
            custom_uploader_args=csp_upload_args,
            service_lookup_timeout_sec=lookup_timeout_sec
        )
        self.jobs[job_id] = upload_image

        upload_image.set_log_handler(
            self._send_job_response
        )
        upload_image.set_result_handler(
            self._send_listen_response
        )
        if nonstop:
            upload_image.upload(oneshot=False)
        else:
            upload_image.upload(oneshot=True)
