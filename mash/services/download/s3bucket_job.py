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
from mash.utils.ec2 import (
    get_session,
    download_file_from_s3_bucket
)
from mash.mash_exceptions import (
    MashJobException,
    MashImageDownloadException
)
from mash.utils.mash_utils import handle_request


class S3BucketDownloadJob(object):
    """
    Implements S3 bucket image download job

    Attributes

    * :attr:`job_id`
      job id number

    * :attr:`job_file`
      job file containing the job description

    * :attr:`download_url`
      S3 bucket URL.
      Includes the `directory` part of the URL if the key object contains some
      directory structure.

    * :attr:`image_name`
      Image name for the download.
      Contains the filename for the image to be downloaded.

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
      Defaults to: '/var/lib/mash/images/{job_id}'.
    """

    def __init__(self, job_config, config):
        self.job_config = job_config
        self.config = config
        try:
            self.job_id = job_config['id']
            self.job_file = job_config['job_file']
            self.download_url = job_config['download_url']
            self.image_name = job_config['image']
            self.last_service = job_config['last_service']
            self.download_account = job_config['download_account']
            self.requesting_user = job_config['requesting_user']
            self.download_type = job_config['download_type']

        except KeyError as e:
            missing_key = e.args[0]
            msg = f'{missing_key} field is required in Mash job doc.'
            raise MashImageDownloadException(msg)

        self.download_directory = os.path.join(
            config.get_download_directory(),
            self.job_id
        )

        self.arch = job_config.get('cloud_architecture', 'x86_64')
        self.notification_email = job_config.get('notification_email', None)
        self.credentials_url = config.get_credentials_url()

        self.log_callback = None
        self.job_status = 'prepared'
        self.progress_log = {}
        self.errors = []
        self.scheduler = None
        self.job_deleted = False

        self.download_credentials = self._request_credentials(
            self.download_account,
            'ec2'
        )
        self.image_filename = ''

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def set_log_handler(self, function):
        self.log_callback = logging.LoggerAdapter(
            function,
            {'job_id': self.job_id}
        )

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
        self.log_callback.info('Job running')

        try:

            boto3_session = get_session(
                self.download_credentials['access_key_id'],
                self.download_credentials['secret_access_key'],
                None
            )
            bucket_name, dir_part_of_object_key = \
                self._get_bucket_name_and_key_from_download_url()

            destination_file = os.path.join(
                self.download_directory,
                self.image_name
            )

            if dir_part_of_object_key:
                full_object_key = os.path.join(
                    dir_part_of_object_key,
                    self.image_name
                )
            else:
                full_object_key = self.image_name

            download_file_from_s3_bucket(
                boto3_session,
                bucket_name,
                full_object_key,
                destination_file
            )
            self.log_callback.info(
                'Downloaded: {0} from {1} S3 bucket to {2}'.format(
                    full_object_key,
                    bucket_name,
                    destination_file
                )
            )
            self.image_filename = destination_file

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
                        'image_file': self.image_filename,
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

    def _get_bucket_name_and_key_from_download_url(self) -> (str, str):
        """
        Returns the bucket name and the 'directory' part of download_url param
        For example: is the download_url provided is
            s3://my-bucket-name/directory1/directory2
        It will return:
            my-bucket-name ,
            /directory1/directory2
        """
        download_url = self.download_url.replace('s3://', '')
        download_url_parts = download_url.split('/', maxsplit=1)
        if len(download_url_parts) > 1:
            return (download_url_parts[0], download_url_parts[1])
        return (download_url, '')

    def _request_credentials(self, account, cloud=None):
        """
        Request credentials from credential service for download_account in aws.

        Only send request if credentials not already populated.
        """
        data = {
            'cloud': cloud,
            'cloud_accounts': [account],
            'requesting_user': self.requesting_user
        }

        try:
            response = handle_request(
                self.credentials_url,
                'credentials/',
                'get',
                job_data=data
            )
            if response:
                creds = response.json()
                return creds[account]
            return {}
        except Exception as e:
            raise MashJobException(
                'Credentials request failed for account: {account}. {exc}'.format(
                    account=account,
                    exc=str(e)
                )
            )
