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
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.base_service import BaseService
from mash.services.uploader.upload_image import UploadImage
from mash.services.uploader.config import UploaderConfig
from mash.utils.json_format import JsonFormat
from mash.csp import CSP


class UploadImageService(BaseService):
    """
    Implements upload to the public cloud network service
    """
    def post_init(self):
        # read config file
        config = UploaderConfig()

        # setup service log file
        self.set_logfile(config.get_log_file(self.service_exchange))

        # upload image instances
        self.jobs = {}

        # upload image instances sending information
        # to a queue for a potentially listening client
        self.clients = {}

        # start job scheduler
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

        # read and launch open jobs
        self.restart_jobs(self._schedule_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(self._process_message, self.service_queue)

        try:
            self.channel.start_consuming()
        except Exception:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.close_connection()

    def _send_job_response(self, job_id, status_message):
        self.log.info(status_message, extra={'job_id': job_id})

    def _send_job_result(
        self, job_id, last_upload_region, trigger_info
    ):
        if self.jobs[job_id]['uploader_result']['status'] != 'failed':
            self.jobs[job_id]['uploader_result']['status'] = \
                trigger_info['job_status']
        region = trigger_info['upload_region']
        self.jobs[job_id]['uploader_result']['source_regions'][region] = \
            trigger_info['cloud_image_id']
        if last_upload_region:
            self.publish_job_result(
                'testing', job_id, JsonFormat.json_message(
                    self.jobs[job_id]['uploader_result']
                )
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
        if 'uploader_job' in job_data:
            job_id = job_data['uploader_job'].get('id', None)
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
        if 'image_file' in service_data:
            system_image_file = service_data['image_file'][0]
            self.jobs[job_id]['system_image_file'] = system_image_file
            self._send_job_response(
                job_id, 'Got image file: {0}'.format(system_image_file)
            )
        if 'credentials' in service_data:
            # NOTE: The response from the credentials service is still
            # work in progress and will change. The current assumption
            # is that service_data['credentials'] contains all information
            # to upload to all target_regions of this job document
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
          "uploader_job": {
            "id": "123",
            "utctime": "now|always|timestring_utc_timezone",
            "cloud_image_name": "name",
            "image_description": "description",
            "provider": "ec2",
            "target_regions": {
                "us-east-1": {
                    "helper_image": "ami-bc5b48d0",
                    "account": "test-aws"
                }
            }
          }
        }
        """
        job_info = self._validate_job_description(data)
        if not job_info['ok']:
            return job_info
        else:
            data = data['uploader_job']
            data['job_file'] = self.persist_job_config(data)
            return self._schedule_job(data)

    def _delete_job(self, job_id):
        """
        Delete job description and stop image upload job
        """
        if job_id not in self.jobs:
            return {
                'ok': False,
                'message': 'Job does not exist, can not delete it'
            }
        else:
            upload_image = self.jobs[job_id]['uploader'][0]
            # delete job file
            try:
                os.remove(upload_image.job_file)
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job deletion failed: {0}'.format(e)
                }
            else:
                # delete upload image job instances
                for upload_image in self.jobs[job_id]['uploader']:
                    del upload_image
                del self.jobs[job_id]
                return {
                    'ok': True,
                    'message': 'Job Deleted'
                }

    def _validate_job_description(self, job_data):
        # validate job description. Currently only Amazon ec2 is supported
        if 'uploader_job' not in job_data:
            return {
                'ok': False,
                'message': 'Invalid job: no uploader_job'
            }
        job = job_data['uploader_job']
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
        if 'image_description' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no cloud image description'
            }
        if 'provider' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no cloud provider'
            }
        if job['provider'] != CSP.ec2:
            return {
                'ok': False,
                'message': 'Invalid job: {0} provider not supported'.format(
                    job['provider']
                )
            }
        if 'target_regions' not in job:
            return {
                'ok': False,
                'message': 'Invalid job: no target regions record'
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

    def _get_uploader_arguments_per_region(self, job_data):
        uploader_args = []
        for region in job_data['target_regions']:
            if job_data['provider'] == CSP.ec2:
                # turn region metadata into EC2ImageUploader compatible format
                uploader_args.append(
                    {
                        'launch_ami':
                            job_data['target_regions'][region]['helper_image'],
                        'region': region
                    }
                )
        return uploader_args

    def _init_job(self, job_data):
        # init empty job hash if not yet done
        job_id = job_data['id']
        csp = job_data['provider']
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
        # init the job result dictionary
        self.jobs[job_id]['uploader_result'] = {
            'id': job_id,
            'cloud_image_name': job_data['cloud_image_name'],
            'source_regions': {},
            'status': None
        }
        self.jobs[job_id]['nonstop'] = nonstop
        self.jobs[job_id]['uploader'] = []
        # bind on the service queue for this job
        self.bind_queue(
            self.service_exchange, job_id, self.service_queue
        )
        # NOTE: If the credentials service is finished, any service
        # which needs credentials has to send a request to the credentials
        # service. The sending of this request is still missing here
        # and needs to be added once the credentials service is done.
        # At the moment the stub credentials service just provides us
        # the information without an extra request. Thus binding the
        # queue is currently enough.
        if csp:
            self.bind_credentials_queue()
            self.consume_credentials_queue(self._process_message)
        return {
            'time': time,
            'nonstop': nonstop
        }

    def _schedule_job(self, job):
        startup = self._init_job(job)
        region_list = self._get_uploader_arguments_per_region(job)
        for index, uploader_args in enumerate(region_list):
            last_upload_region = False
            if index == len(region_list) - 1:
                last_upload_region = True
            job_args = [
                job, startup['nonstop'], uploader_args, last_upload_region
            ]
            if startup['time']:
                self.scheduler.add_job(
                    self._start_job, 'date', args=job_args,
                    run_date=startup['time'],
                    timezone='utc'
                )
            else:
                self.scheduler.add_job(
                    self._start_job, args=job_args
                )

    def _wait_until_ready(self, job_id):
        while True:
            if job_id in self.jobs and 'ready' in self.jobs[job_id]:
                break
            time.sleep(1)

    def _image_already_uploading(self, job_id, uploader):
        if 'system_image_file' not in self.jobs[job_id]:
            return False
        system_image_file = self.jobs[job_id]['system_image_file']
        if uploader.system_image_file != system_image_file:
            return False
        return True

    def _start_job(self, job, nonstop, uploader_args, last_upload_region):
        job_id = job['id']
        delay_time_sec = 30
        csp_name = job['provider']

        self._send_job_response(
            job_id, 'Region [{0}]: Waiting for image/credentials data'.format(
                uploader_args['region']
            )
        )
        self._wait_until_ready(job_id)

        # NOTE: As we have not finished the credentials service the
        # current assumption is that the credentials_token contains
        # credentials valid for all regions we upload to. This is
        # surely not correct and will be changed. Once the credentials
        # information is region specific the construction of the
        # UploadImage instance must make sure to take this into
        # account
        upload_image = UploadImage(
            job_id, job['job_file'], nonstop, csp_name,
            self.jobs[job_id]['credentials_token'],
            job['cloud_image_name'],
            job['image_description'],
            last_upload_region,
            uploader_args
        )
        self.jobs[job_id]['uploader'].append(upload_image)
        upload_image.set_log_handler(
            self._send_job_response
        )
        upload_image.set_result_handler(
            self._send_job_result
        )
        while self.jobs[job_id]['ready']:
            if not self._image_already_uploading(job_id, upload_image):
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
