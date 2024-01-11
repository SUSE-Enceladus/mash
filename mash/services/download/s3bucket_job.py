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
import re

from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED
# project
from mash.services.base_defaults import Defaults


class S3BucketDownloadJob(object):
    """
    Implements S3 bucket image download job

    Attributes

    * :attr:`job_id`
      job id number

    * :attr:`job_file`
      job file containing the job description

    * :attr:`download_url`
      S3 bucket URL

    * :attr:`last_service`
      The last service for the job.

    * :attr:`log_callback`
      The callback that is used for logs.

    * :attr:`notification_email`
      The email address to send notifications to.

    * :attr:`download_account`
      The account that will be used for the S3 download.

    * :attr:`download_credentials`
      The dictionary containing the credentials for S3 bucket authentication.
      Credentials must be setup to provide list and download permission on the
      S3 bucket.

    * :attr:`download_directory`
      Target download directory name where the files will be downloaded/stored.
      Defaults to: '/var/lib/mash/images/'.
    """

    def __init__(
        self,
        job_id,
        job_file,
        download_url,
        image_name,
        cloud_architecture,
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
        self.image_filename = ''

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def start_watchdog(self, isotime=None):
        """
        Start a background job which fetches the image from the S3 bucket.

        The job is started at a given data/time which must
        be the result of a isoformat() call. If no date/time is
        specified the job runs immediately.

        :param string isotime: date and time by isoformat()
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
        pass

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

    def _get_regex_for_filename(self, image_name, cloud):
        """
        Provides the regex to filter all the available images (with different
        dates) for the image_name and cloud provided
        """
        image_name_date = ''
        file_extension = ''
        date_regex = r'-v(?P<date>\d{8})-'

        date_match = re.search(date_regex, image_name)
        if date_match:
            image_name_date = date_match.group('date')
        else:
            self.log_callback(f'Unable to find date pattern in {image_name}')
            return ''

        # File name adjustments dependant on the cloud
        if cloud in ['azure', 'gce']:
            # remove the first '-' delimited segment
            image_name = re.sub('^[^-]*-', '', image_name)

        if cloud == 'ec2':
            file_extension = '.raw.xz'
        elif cloud == 'azure':
            file_extension = '.vhdfixed.xz'
        elif cloud == 'gce':
            file_extension = '.tar.gz'

        filename_regex = re.escape(image_name + file_extension)

        # date part substitution
        filename_regex = \
            '^' + \
            filename_regex.replace(
                image_name_date,
                r'(?P<date>\d{8})'
            ) + \
            '$'
        return filename_regex
