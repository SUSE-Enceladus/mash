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
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.base_service import BaseService
from mash.services.uploader.upload_image import UploadImage
from mash.utils.json_format import JsonFormat
from mash.csp import CSP
from mash.services.status_levels import FAILED, SUCCESS


class UploadImageService(BaseService):
    """
    Implements upload to the public cloud network service
    """
    def post_init(self):
        # setup service log file
        self.set_logfile(self.config.get_log_file(self.service_exchange))

        # upload image instances
        self.jobs = {}

        # upload image instances sending information
        # to a queue for a potentially listening client
        self.clients = {}

        # start job scheduler
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

        # Consume credentials response queue
        self.bind_credentials_queue()
        self.consume_credentials_queue(self._process_message)

        # read and launch open jobs
        self.restart_jobs(self._schedule_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(self._process_message, self.service_queue)
        self.consume_queue(self._process_message, self.listener_queue)

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
                    {'uploader_result': self.jobs[job_id]['uploader_result']}
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
        if 'uploader_job' in job_data:
            self._handle_jobs(job_data)
        elif 'jwt_token' in job_data:
            self._handle_credentials(job_data)
        elif 'obs_result' in job_data:
            self._handle_obs_image(job_data)
        else:
            self._send_control_response(
                {
                    'ok': False,
                    'message': 'No idea what to do with: {0}'.format(job_data)
                }
            )

    def _handle_jobs(self, job_data):
        """
        handle uploader job document
        """
        job_id = job_data['uploader_job'].get('id', None)
        self.log.info(
            JsonFormat.json_message(job_data),
            extra={'job_id': job_id}
        )
        result = self._add_job(job_data)
        if result:
            self._send_control_response(result, job_id)

    def _handle_obs_image(self, job_data):
        obs_result = job_data['obs_result']
        if 'id' in obs_result:
            job_id = obs_result['id']

            if obs_result.get('status') == SUCCESS \
                    and 'image_file' in obs_result:
                self._set_job(job_id)
                system_image_file = obs_result['image_file'][0]
                self.jobs[job_id]['system_image_file'] = system_image_file
                self._send_job_response(
                    job_id, 'Got image file: {0}'.format(system_image_file)
                )
                self._check_ready(job_id)
            else:
                result = self._delete_job(job_id)
                self._send_control_response(result, job_id)
                self.publish_job_result(
                    'testing', job_id, JsonFormat.json_message(
                        {
                            'uploader_result': {
                                'id': job_id,
                                'status': obs_result.get('status') or FAILED
                            }
                        }
                    )
                )

    def _handle_credentials(self, job_data):
        job_id, credentials = self.decode_credentials(job_data)
        if job_id:
            self._set_job(job_id)
            self.jobs[job_id]['credentials'] = credentials
            self._send_job_response(
                job_id, 'Got credentials data'
            )
            self._check_ready(job_id)

    def _set_job(self, job_id):
        if job_id not in self.jobs:
            self.jobs[job_id] = {}

    def _check_ready(self, job_id):
        if 'system_image_file' in self.jobs[job_id] and \
           'credentials' in self.jobs[job_id]:
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
            self.unbind_queue(
                self.listener_queue, self.service_exchange, job_id
            )
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

    def _get_uploader_arguments_per_region(self, job_data):
        uploader_args = []
        for region in job_data['target_regions']:
            if job_data['provider'] == CSP.ec2:
                # turn region metadata into EC2ImageUploader compatible format
                uploader_args.append(
                    {
                        'launch_ami':
                            job_data['target_regions'][region]['helper_image'],
                        'account':
                            job_data['target_regions'][region]['account'],
                        'region': region
                    }
                )
            elif job_data['provider'] == CSP.azure:
                # turn region metadata into AzureImageUploader compatible format
                uploader_args.append(
                    {
                        'resource_group':
                            job_data['target_regions'][region]['resource_group'],
                        'container_name':
                            job_data['target_regions'][region]['container_name'],
                        'storage_account':
                            job_data['target_regions'][region]['storage_account'],
                        'account':
                            job_data['target_regions'][region]['account'],
                        'region': region
                    }
                )
            elif job_data['provider'] == CSP.gce:
                # turn region metadata into GCEImageUploader compatible format
                uploader_args.append(
                    {
                        'account': job_data['target_regions'][region]['account'],
                        'bucket': job_data['target_regions'][region]['bucket'],
                        'region': region
                    }
                )
        return uploader_args

    def _init_job(self, job_data):
        # init empty job hash if not yet done
        job_id = job_data['id']
        if job_id not in self.jobs:
            self.jobs[job_id] = {}
        # get us the time when to start this job
        time = job_data['utctime']

        if time == 'always':
            nonstop = True
        else:
            nonstop = False

        # init the job result dictionary
        self.jobs[job_id]['uploader_result'] = {
            'id': job_id,
            'cloud_image_name': job_data['cloud_image_name'],
            'source_regions': {},
            'status': None
        }
        self.jobs[job_id]['nonstop'] = nonstop
        self.jobs[job_id]['uploader'] = []
        # send request for credentials
        self.publish_credentials_request(job_id)
        return {'nonstop': nonstop}

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

        upload_image = UploadImage(
            job_id, job['job_file'], nonstop, csp_name,
            self.jobs[job_id]['credentials'][uploader_args['account']],
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
