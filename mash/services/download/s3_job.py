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
import re
import os

from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED
# project
from mash.services.base_defaults import Defaults
from mash.utils.ec2 import (
    get_client,
    get_file_list_from_s3_bucket
)


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
        cloud,
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
        self.cloud = cloud
        self.image_filename = ''

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

    def _get_latest_image_filename(self, s3_client, bucket_name, image_name):
        bucket_filenames = get_file_list_from_s3_bucket(
            s3_client=s3_client,
            bucket_name=bucket_name
        )
        filename_regex = self.get_regex_for_filename(image_name)
        matching_filenames = self._get_matching_filenames(
            bucket_filenames,
            filename_regex
        )

    def _get_regex_for_filename(self, image_name, cloud):
        date = ''
        extension_name = ''
        date_regex = r'-v(?P<date>\d{8})-'
        date_match = re.search(date_regex, image_name)
        if date_match:
            date = date_match.group('date')
        else:
            self.log_callback(f'Unable to find date pattern in {image_name}')
            return ''

        if cloud in ['azure', 'gce']:
            # removing the first '-' delimited segment for these providers
            image_name = re.sub('^[^-]*-', '', image_name)
        if cloud == 'ec2':
            extension_name = '.raw.xz'
        elif cloud == 'azure':
            extension_name = '.vhdfixed.xz'
        elif cloud == 'gce':
            extension_name = '.tar.gz'

        filename_regex = re.escape(image_name + extension_name)

        filename_regex = \
            '^' + \
            filename_regex.replace(
                date,
                r'(?P<date>\d{8})'
            ) + \
            '$'
        return filename_regex

    def _get_matching_filenames(self, filenames, regex):
        matches = []
        compiled_regex = re.compile(regex)
        for filename in filenames:
            if compiled_regex.search(filename):
                matches.append(filename)
        return matches

    def _get_latest_filename(self, filenames, filename_regex):
        compiled_regex = re.compile(filename_regex)
        latest_image_filename = filenames[0]
        latest_image_timestamp = datetime.strptime(
            compiled_regex.search(latest_image_filename).group('date'),
            '%Y%m%d'
        )
        if len(filenames) == 1:
            return latest_image_filename

        for filename in filenames[1:]:
            timestamp = datetime.strptime(
                compiled_regex.search(filename).group('date'),
                '%Y%m%d'
            )
            if timestamp > latest_image_timestamp:
                latest_image_filename = filename
                latest_image_timestamp = timestamp
        return latest_image_filename
