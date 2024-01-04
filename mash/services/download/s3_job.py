# Copyright (c) 2023 SUSE LLC.  All rights reserved.
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


import logging
import os

from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED
# project
from mash.services.base_defaults import Defaults
from mash.utils.ec2 import get_client


class S3DownloadJob(object):
    """
    Implements S3 bucket image download job

    Attributes

    * :attr:`job_id`
      job id number

    * :attr:`job_file`
      job file containing the job description

    * :attr:`download_url`
      S3 bucket URL

    * :attr:`download_directory`
      Download directory name, defaults to: /tmp

    * :attr:`last_service`
      The last service for the job.


    """
    def __init__(
        self,
        job_id,
        job_file,
        download_url,
        image_name,
        cloud_architecture,
        s3_download_file_prefix,
        s3_download_file_suffix,
        last_service,
        log_callback,
        notification_email,
        download_account,
        download_credentials,
        download_directory=Defaults.get_download_dir(),
    ):
        self.job_id = job_id
        self.job_file = job_file
        self.download_directory = os.path.join(download_directory, job_id)
        self.download_url = download_url
        self.image_name = image_name
        self.last_service = last_service
        self.log_callback = logging.LoggerAdapter(
            log_callback,
            {'job_id': self.job_id}
        )
        self.notification_email = notification_email
        self.job_status = 'prepared'
        self.progress_log = {}
        self.errors = []
        self.scheduler = None
        self.job_deleted = False
        self.download_account = download_account
        self.download_credentials = download_credentials
        self.s3_download_file_prefix = s3_download_file_prefix
        self.s3_download_file_suffix = s3_download_file_suffix
        self.image_filename = (
            f'{s3_download_file_prefix}'
            f'{image_name}'
            f'-{cloud_architecture}'
            f'{s3_download_file_suffix}'
        )

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def start_watchdog(self, isotime=None):
        """
        Start a background job which fetches the image from the S3 bucket.

        The job is started at a given data/time which must
        be the result of a isoformat() call. If no data/time is
        specified the job runs immediately.

        :param string isotime: data and time by isoformat()
        """
        job_time = None

        if isotime:
            job_time = datetime.strptime(isotime[:19], '%Y-%m-%dT%H:%M:%S')

        self.scheduler = BackgroundScheduler(timezone=utc)

        self.job = self.scheduler.add_job(
            self._download_image_file,
            'date',
            run_date=job_time,
            timezone='utc'
        )
        self.scheduler.add_listener(
            self._job_submit_event, EVENT_JOB_SUBMITTED
        )
        self.scheduler.start()

    def stop_watchdog(self):
        """
        Remove active job from scheduler

        Current image status is retained
        """
        try:
            self.job.remove()
            self.job_deleted = True
        except Exception:
            pass

    def _job_submit_event(self, event):
        self.log_callback.info('Oneshot Job submitted')

    def _download_image_file(self):
        """ Download the image file to the destination directory"""
        self.log_callback.info('Job running')

        try:

            client = get_client(
                's3',
                self.download_credentials['access_key_id'],
                self.download_credentials['secret_access_key'],
                None
            )
            destination_file = os.path.join(
                self.download_directory, self.image_filename
            )
            client.download_fileobj(
                self.download_url,
                self.image_filename,
                destination_file
            )
            self.log_callback.info('Downloaded: {0} from {1} S3 bucket'.format(
                self.image_filename,
                self.download_url
            ))

            # job finished successfully
            self.job_status = 'success'
            self.log_callback.info(
                'Job status: {0}'.format(self.job_status)
            )
            self._result_callback()
            self.log_callback.info('Job done')
        except Exception as issue:

            msg = '{0}: {1}'.format(type(issue).__name__, issue)
            self.job_status = 'failed'
            self.errors.append(msg)
            self.log_callback.error(msg)
            self._result_callback()

    def _result_callback(self):
        if self.result_callback:
            self.result_callback(
                self.job_id, {
                    'download_result': {
                        'id': self.job_id,
                        'image_file': os.path.join(
                            self.download_directory,
                            self.image_filename
                        ),
                        'status': self.job_status,
                        'errors': self.errors,
                        'notification_email': self.notification_email,
                        'last_service': self.last_service,
                        'build_time':
                            self._get_build_time(self.image_name),
                    }
                }
            )

    def _get_build_time(self, image_name):
        return 'unknown'

    def _job_skipped_event(self, event):
        # Job is still active while the next _update_image_status
        # event was scheduled. In this case we just skip the event
        # and keep the active job waiting for an obs change
        pass
