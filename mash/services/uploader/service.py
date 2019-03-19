# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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
import datetime
import os
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

# project
from mash.services.mash_service import MashService
from mash.services.uploader.upload_image import UploadImage
from mash.utils.json_format import JsonFormat
from mash.csp import CSP
from mash.services.status_levels import (
    FAILED,
    SUCCESS
)


class UploadImageService(MashService):
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
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.scheduler.shutdown()
            self.close_connection()

    def _job_log(self, job_id, message):
        self.log.info(message, extra={'job_id': job_id})

    def _publish_job_result(
        self, job_id, publish_on_failed_job, status=None
    ):
        """
        Publish current uploader result to testing queue
        """
        if status:
            self.jobs[job_id]['uploader_result']['status'] = status
        job_status = self.jobs[job_id]['uploader_result']['status']
        if (job_status == FAILED and publish_on_failed_job is False) \
                or self.jobs[job_id]['last_service'] == self.service_exchange:
            return
        self.publish_job_result(
            self.next_service, JsonFormat.json_message(
                {'uploader_result': self.jobs[job_id]['uploader_result']}
            )
        )

    def _send_job_result(self, job_id, trigger_info):
        """
        UploadImage result callback

        Update the current uploader result with the information
        from the UploadImage instance triggered by the callback
        and publishes the overall result if the upload to the
        last region has finished
        """
        job = self.jobs[job_id]
        if job['uploader_result']['status'] != 'failed':
            job['uploader_result']['status'] = trigger_info['job_status']

        region = trigger_info['upload_region']

        job['regions_finished'][region] = True
        job['uploader_result']['source_regions'][region] = \
            trigger_info['cloud_image_id']

        if trigger_info['error_msg']:
            job['error_msg'] = trigger_info['error_msg']

        last_region = True
        for region in job['job_config']['target_regions']:
            if not job['regions_finished'].get(region):
                last_region = False
                break

        if last_region:
            if not job['utctime'] == 'always':
                self._publish_job_result(job_id, publish_on_failed_job=True)
                self._delete_job(job_id)
            else:
                self._publish_job_result(job_id, publish_on_failed_job=False)

            if job['uploader']:
                iteration_count = job['uploader'][-1].iteration_count
            else:
                iteration_count = 1

            self.send_email_notification(
                job_id, job['notification_email'],
                job['notification_type'],
                job['uploader_result']['status'],
                job['utctime'],
                job['last_service'],
                iteration_count,
                job.get('error_msg')
            )

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
            "cloud": "ec2",
            "target_regions": {
                "us-east-1": {
                    "helper_image": "ami-bc5b48d0",
                    "account": "test-aws"
                }
            },
            "notification_email": "test@fake.com",
            "notification_type": "single"
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
            job_config['cloud_image_name'] = self._set_upload_date(
                job_config['cloud_image_name']
            )

            self.jobs[job_id] = {
                'job_config': job_config,
                'last_service': job_config.get('last_service'),
                'utctime': job_config.get('utctime'),
                'cloud_architecture': job_config.get('cloud_architecture'),
                'job_file': self.persist_job_config(job_config),
                'credentials': None,
                'system_image_file': None,
                'uploader': [],
                'uploader_result': {
                    'id': job_id,
                    'cloud_image_name': job_config['cloud_image_name'],
                    'source_regions': {},
                    'status': None
                },
                'notification_email': job_config.get('notification_email'),
                'notification_type': job_config.get('notification_type'),
                'regions_finished': {}
            }
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
                self._publish_job_result(
                    job_id, publish_on_failed_job=True, status=obs_status
                )
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
            if self.jobs[job_id]['last_service'] == self.service_exchange:
                # Send delete message to credentials
                # if this is the last service.
                self.publish_credentials_delete(job_id)

            # delete job file
            try:
                os.remove(self.jobs[job_id]['job_file'])
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
            'billing_codes':
                job_config['target_regions'][region]['billing_codes'],
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
            if job_config['cloud'] == CSP.ec2:
                # turn region metadata into EC2ImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_ec2(job_config, region)
                )
            elif job_config['cloud'] == CSP.azure:
                # turn region metadata into AzureImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_azure(job_config, region)
                )
            elif job_config['cloud'] == CSP.gce:
                # turn region metadata into GCEImageUploader compatible format
                uploader_args.append(
                    self._get_uploader_arguments_gce(job_config, region)
                )
        return uploader_args

    def _schedule_job(self, job_id):
        region_list = self._get_uploader_arguments_per_region(
            self.jobs[job_id]['job_config']
        )
        for uploader_args in region_list:
            job_args = [job_id, uploader_args]
            self.scheduler.add_job(
                self._start_job, args=job_args
            )

    def _start_job(self, job_id, uploader_args):
        self._job_log(
            job_id, 'Region [{0}]: Starting Upload'.format(
                uploader_args['region']
            )
        )

        arch = self.jobs[job_id]['job_config'].get(
            'cloud_architecture', 'x86_64'
        )

        upload_image = UploadImage(
            job_id, self.jobs[job_id]['job_file'],
            self.jobs[job_id]['job_config']['cloud'],
            self.jobs[job_id]['credentials'][uploader_args['account']],
            self.jobs[job_id]['job_config']['cloud_image_name'],
            self.jobs[job_id]['job_config']['image_description'],
            uploader_args['region'],
            uploader_args,
            arch
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

    @staticmethod
    def _set_upload_date(cloud_image_name):
        today = datetime.date.today().strftime("%Y%m%d")

        try:
            cloud_image_name = cloud_image_name.format(date=today)
        except KeyError:
            # Ignore unknown format strings.
            pass

        return cloud_image_name
