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
import time
import dateutil.parser
from distutils.dir_util import mkpath
from tempfile import NamedTemporaryFile
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

        # setup service data directories
        self.job_directory = Defaults.get_jobs_dir()

        mkpath(self.job_directory)

        # upload image instances
        self.jobs = {}

        # upload image instances sending information
        # to a queue for a potentially listening client
        self.clients = {}

        # start job scheduler
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

        # read and launch open jobs
        for job_file in os.listdir(self.job_directory):
            self._schedule_job(os.sep.join([self.job_directory, job_file]))

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(self._process_message)

        try:
            self.channel.start_consuming()
        except Exception as e:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.close_connection()

    def _send_job_response(self, job_id, status_message):
        self.log.info(status_message, extra={'job_id': job_id})

    def _send_job_result_for_testing(self, job_id, trigger_info):
        self.jobs[job_id]['system_image_file_uploaded'] = \
            self.jobs[job_id]['system_image_file']
        self.publish_job_result(
            'testing', job_id, JsonFormat.json_message(trigger_info)
        )
        if not self.jobs[job_id]['nonstop']:
            self._delete_job(job_id)

    def _send_control_response(self, result, job_id=None):
        message = result['message']

        job_metadata = {}
        if job_id:
            job_metadata['job_id'] = job_id

        if result['ok']:
            self.log.info(message, extra=job_metadata)
        else:
            self.log.error(message, extra=job_metadata)

    def _process_message(self, message):
        message.ack()
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
        if message.method['routing_key'] == 'job_document':
            self._handle_jobs(job_data)
        else:
            self._handle_service_data(message, job_data)

    def _handle_jobs(self, job_data):
        """
        handle uploader job document
        """
        job_id = None
        if 'uploadjob' in job_data:
            job_id = job_data['uploadjob'].get('id', None)
            self.log.info(
                JsonFormat.json_message(job_data),
                extra={'job_id': job_id}
            )
            result = self._add_job(job_data)
        else:
            result = {
                'ok': False,
                'message': 'No idea what to do with: {0}'.format(job_data)
            }
        if result:
            self._send_control_response(result, job_id)

    def _handle_service_data(self, message, service_data):
        job_id = message.method['routing_key']
        if job_id not in self.jobs:
            self.jobs[job_id] = {}
        if 'image_source' in service_data:
            system_image_file = service_data['image_source'][0]
            self.jobs[job_id]['system_image_file'] = system_image_file
            self._send_job_response(
                job_id, 'Got image file: {0}'.format(system_image_file)
            )
        if 'credentials' in service_data:
            self.jobs[job_id]['credentials_token'] = service_data['credentials']
            self._send_job_response(
                job_id, 'Got credentials data'
            )
        if 'system_image_file' in self.jobs[job_id] and \
           'credentials_token' in self.jobs[job_id]:
            self.jobs[job_id]['ready'] = True

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
            job_file = NamedTemporaryFile(
                prefix='job-', suffix='.json',
                dir=self.job_directory, delete=False
            )
            with open(job_file.name, 'w') as job_description:
                job_description.write(JsonFormat.json_message(data))
            return self._schedule_job(job_file.name)

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
            upload_image = self.jobs[job_id]['uploader']
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
                del self.jobs[job_id]

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

    def _get_csp_name(self, job_data):
        if 'ec2' in job_data:
            return 'ec2'

    def _init_job(self, job_data):
        # init empty job hash if not yet done
        job_id = job_data['id']
        if job_id not in self.jobs:
            self.jobs[job_id] = {}
        # get us the time when to start this job
        time = job_data['utctime']
        nonstop = False
        if time == 'now':
            time = None
        elif time == 'always':
            time = None
            nonstop = True
        else:
            time = dateutil.parser.parse(job_data['utctime']).isoformat()
        self.jobs[job_id]['nonstop'] = nonstop
        # bind on the credentials queue for this csp
        if 'ec2' in job_data:
            csp = 'ec2'
            self.bind_credentials_queue(job_id, csp)
            self.consume_credentials_queue(
                self._process_message, csp
            )
        return {
            'time': time,
            'nonstop': nonstop
        }

    def _schedule_job(self, job_file):
        with open(job_file) as job_description:
            job = JsonFormat.json_load(job_description)['uploadjob']

        startup = self._init_job(job)

        if startup['time']:
            self.scheduler.add_job(
                self._start_job, 'date',
                args=[job_file, job, startup['nonstop']],
                run_date=startup['time'],
                timezone='utc'
            )
        else:
            self.scheduler.add_job(
                self._start_job,
                args=[job_file, job, startup['nonstop']]
            )

    def _wait_until_ready(self, job_id):
        while True:
            if job_id in self.jobs and 'ready' in self.jobs[job_id]:
                break
            time.sleep(1)

    def _image_already_uploaded(self, job_id):
        if 'system_image_file_uploaded' not in self.jobs[job_id]:
            return False
        if 'system_image_file' not in self.jobs[job_id]:
            return False
        image_file = self.jobs[job_id]['system_image_file']
        image_file_uploaded = self.jobs[job_id]['system_image_file_uploaded']
        if image_file != image_file_uploaded:
            return False
        self._send_job_response(
            job_id, 'Image already uploaded'
        )
        return True

    def _start_job(self, job_file, job, nonstop):
        job_id = job['id']
        csp_name = None
        csp_upload_args = None
        if 'ec2' in job:
            csp_name = 'ec2'
            csp_upload_args = job[csp_name]

        self._send_job_response(
            job_id, 'Waiting for image and credentials data'
        )

        self._wait_until_ready(job_id)

        # upload to the cloud. For nonstop uploads the upload is
        # repeated after a delay and only if the image file has
        # changed but with the same access credentials
        delay_time_sec = 30
        upload_image = UploadImage(
            job_id, job_file, nonstop, csp_name,
            self.jobs[job_id]['credentials_token'],
            job['cloud_image_name'], job['cloud_image_description'],
            custom_uploader_args=csp_upload_args
        )
        self.jobs[job_id]['uploader'] = upload_image
        upload_image.set_log_handler(
            self._send_job_response
        )
        upload_image.set_result_handler(
            self._send_job_result_for_testing
        )
        while self.jobs[job_id]['ready']:
            if not self._image_already_uploaded(job_id):
                upload_image.set_image_file(
                    self.jobs[job_id]['system_image_file']
                )
                upload_image.upload()
            if nonstop:
                self._send_job_response(
                    job_id, 'Waiting {0}sec before next try...'.format(
                        delay_time_sec
                    )
                )
                time.sleep(delay_time_sec)
            else:
                break
