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
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.base_service import BaseService
from mash.services.uploader.upload_image import UploadImage
from mash.utils.json_format import JsonFormat
from mash.csp import CSP
from mash.services.status_levels import (
    FAILED,
    SUCCESS
)


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
        self.consume_credentials_queue(self._process_credentials)

        # read and launch open jobs
        self.restart_jobs(self._init_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(self._process_job, self.service_queue)
        self.consume_queue(self._process_obs_result, self.listener_queue)

        try:
            self.channel.start_consuming()
        except Exception:
            raise
        finally:
            self.close_connection()

    def _job_log(self, job_id, message):
        self.log.info(message, extra={'job_id': job_id})

    def _publish_job_result(self, job_id, status=None):
        """
        Publish current uploader result to testing queue
        """
        if status:
            self.jobs[job_id]['uploader_result']['status'] = status
        self.publish_job_result(
            'testing', job_id, JsonFormat.json_message(
                {'uploader_result': self.jobs[job_id]['uploader_result']}
            )
        )

    def _send_job_result(self, job_id, last_upload_region, trigger_info):
        """
        UploadImage result callback

        Update the current uploader result with the information
        from the UploadImage instance triggered by the callback
        and publishes the overall result if the upload to the
        last region has finished
        """
        if self.jobs[job_id]['uploader_result']['status'] != 'failed':
            self.jobs[job_id]['uploader_result']['status'] = \
                trigger_info['job_status']
        region = trigger_info['upload_region']
        self.jobs[job_id]['uploader_result']['source_regions'][region] = \
            trigger_info['cloud_image_id']
        if last_upload_region:
            self._publish_job_result(job_id)
            if not self.jobs[job_id]['utctime'] == 'always':
                self._delete_job(job_id)

    def _process_job(self, message):
        """
        Add a new job description file and initialize new upload job

        job description example:

        {
          "uploader_job": {
            "id": "123",
            "utctime": "now|always,
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
        try:
            job_data = JsonFormat.json_loads(format(message.body))
            self._init_job(job_data)
        except Exception as issue:
            self.log.error(
                'Error processing job: {0}: {1}'.format(message.body, issue)
            )
        message.ack()

    def _process_obs_result(self, message):
        """
        Listen on obs service event
        """
        try:
            job_data = JsonFormat.json_loads(format(message.body))
            self._handle_obs_image(job_data)
        except Exception as issue:
            self.log.error(
                'Invalid obs result: {0}: {1}'.format(message.body, issue)
            )
        message.ack()

    def _process_credentials(self, message):
        """
        Listen on credentials service event
        """
        try:
            job_data = JsonFormat.json_loads(format(message.body))
            self._handle_credentials(job_data)
        except Exception as issue:
            self.log.error(
                'Invalid credentials: {0}: {1}'.format(message.body, issue)
            )
        message.ack()

    def _init_job(self, job_data):
        """
        Initialize new job

        Bind listener queue to receive obs service result
        """
        if 'uploader_job' in job_data:
            job_config = job_data['uploader_job']
        else:
            self._job_log(job_data['id'], 'Respawn preserved job')
            job_config = job_data
        job_id = job_config['id']
        if job_id not in self.jobs:
            self.jobs[job_id] = {
                'job_config': job_config,
                'utctime': job_config.get('utctime'),
                'job_file': self.persist_job_config(job_config),
                'credentials': None,
                'system_image_file': None,
                'uploader': [],
                'uploader_result': {
                    'id': job_id,
                    'cloud_image_name': job_config['cloud_image_name'],
                    'source_regions': {},
                    'status': None
                }
            }
            self.bind_listener_queue(job_id)
            self._job_log(
                job_id, 'Job queued, awaiting obs result'
            )

    def _handle_obs_image(self, job_data):
        """
        Read result from obs service

        On success run uploader job if credentials are present,
        if not request credentials

        On failure delete job and publish uploader job result
        for testing service to keep the service queue active
        """
        obs_result = job_data['obs_result']
        job_id = obs_result.get('id')
        obs_status = obs_result.get('status', FAILED)
        if job_id and job_id in self.jobs:
            if obs_status == SUCCESS and 'image_file' in obs_result:
                system_image_file = obs_result['image_file'][0]
                self.jobs[job_id]['system_image_file'] = system_image_file
                self._job_log(
                    job_id, 'Got image file: {0}'.format(system_image_file)
                )
                if self.jobs[job_id]['credentials']:
                    self._schedule_job(job_id)
                else:
                    self.publish_credentials_request(job_id)
            else:
                self._publish_job_result(job_id, status=obs_status)
                self._delete_job(job_id)
                self._job_log(
                    job_id, 'OBS service sent failed result, dequeue uploader'
                )

    def _handle_credentials(self, job_data):
        """
        Read and decode credentials

        On success run uploader job if system image file is present
        """
        job_id, credentials = self.decode_credentials(job_data)
        if job_id and job_id in self.jobs:
            self.jobs[job_id]['credentials'] = credentials
            if self.jobs[job_id]['system_image_file']:
                self._schedule_job(job_id)

    def _delete_job(self, job_id):
        """
        Delete job description and stop image upload job
        """
        if job_id not in self.jobs:
            self._job_log(job_id, 'Job does not exist')
        else:
            self.unbind_queue(
                self.listener_queue, self.service_exchange, job_id
            )
            upload_image = self.jobs[job_id]['uploader'][0]
            # delete job file
            try:
                os.remove(upload_image.job_file)
            except Exception as issue:
                self._job_log(
                    job_id, 'Job deletion failed: {0}'.format(issue)
                )
            else:
                # delete upload image job instances
                for upload_image in self.jobs[job_id]['uploader']:
                    del upload_image
                del self.jobs[job_id]
                self._job_log(
                    job_id, 'Job Deleted'
                )

    def _get_uploader_arguments_ec2(self, job_config, region):
        return {
            'launch_ami':
                job_config['target_regions'][region]['helper_image'],
            'account':
                job_config['target_regions'][region]['account'],
            'region': region
        }

    def _get_uploader_arguments_azure(self, job_config, region):
        return {
            'resource_group':
                job_config['target_regions'][region]['resource_group'],
            'container':
                job_config['target_regions'][region]['container'],
            'storage_account':
                job_config['target_regions'][region]['storage_account'],
            'account':
                job_config['target_regions'][region]['account'],
            'region': region
        }

    def _get_uploader_arguments_gce(self, job_config, region):
        return {
            'account':
                job_config['target_regions'][region]['account'],
            'bucket':
                job_config['target_regions'][region]['bucket'],
            'family':
                job_config['target_regions'][region]['family'],
            'region':
                region
        }

    def _get_uploader_arguments_per_region(self, job_config):
        uploader_args = []
        for region in job_config['target_regions']:
            if job_config['provider'] == CSP.ec2:
                # turn region metadata into EC2ImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_ec2(job_config, region)
                )
            elif job_config['provider'] == CSP.azure:
                # turn region metadata into AzureImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_azure(job_config, region)
                )
            elif job_config['provider'] == CSP.gce:
                # turn region metadata into GCEImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_gce(job_config, region)
                )
        return uploader_args

    def _schedule_job(self, job_id):
        region_list = self._get_uploader_arguments_per_region(
            self.jobs[job_id]['job_config']
        )
        for index, uploader_args in enumerate(region_list):
            last_upload_region = False
            if index == len(region_list) - 1:
                last_upload_region = True
            job_args = [
                job_id, uploader_args, last_upload_region
            ]
            self.scheduler.add_job(
                self._start_job, args=job_args
            )

    def _start_job(self, job_id, uploader_args, last_upload_region):
        self._job_log(
            job_id, 'Region [{0}]: Starting Upload'.format(
                uploader_args['region']
            )
        )
        upload_image = UploadImage(
            job_id, self.jobs[job_id]['job_file'],
            self.jobs[job_id]['job_config']['provider'],
            self.jobs[job_id]['credentials'][uploader_args['account']],
            self.jobs[job_id]['job_config']['cloud_image_name'],
            self.jobs[job_id]['job_config']['image_description'],
            last_upload_region,
            uploader_args
        )
        self.jobs[job_id]['uploader'].append(upload_image)
        upload_image.set_log_handler(
            self._job_log
        )
        upload_image.set_result_handler(
            self._send_job_result
        )
        upload_image.set_image_file(
            self.jobs[job_id]['system_image_file']
        )
        upload_image.upload()
