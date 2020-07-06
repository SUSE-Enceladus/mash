# Copyright (c) 2019 SUSE Software Solutions Germany GmbH.  All rights reserved.
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

from os import stat, path

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.ec2 import get_client
from mash.services.status_levels import SUCCESS


class S3BucketUploadJob(MashJob):
    """
    Implements raw image upload to Amazon S3 bucket
    """

    def post_init(self):
        self.cloud = 'ec2'
        self._image_size = 0
        self._total_bytes_transferred = 0
        self._last_percentage_logged = 0
        self._percentage_log_step = 20

        try:
            self.account = self.job_config['raw_image_upload_account']
            self.location = self.job_config['raw_image_upload_location']
        except KeyError as error:
            raise MashUploadException(
                'S3 bucket upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def _log_progress(self, bytes_transferred):
        self._total_bytes_transferred += bytes_transferred
        percent_transferred = (self._total_bytes_transferred * 100) / self._image_size
        if percent_transferred >= \
           (self._last_percentage_logged + self._percentage_log_step):
            self._last_percentage_logged = int(
                percent_transferred - (percent_transferred % self._percentage_log_step)
            )
            self.log_callback.info('Raw image {progress}% uploaded.'.format(
                progress=str(self._last_percentage_logged)
            ))

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading raw image.')

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        # Possible values for location:
        # bucket
        # bucket/file.path or bucket/path/to/file.path
        # bucket/path/to/
        location_args = str.split(self.location, '/', 1)
        bucket_name = location_args[0]

        try:
            bucket_path = location_args[1]
        except IndexError:
            bucket_path = ''

        if self.status_msg['cloud_image_name']:
            # take suffix from file name, should always consist of two parts
            suffix = '.'.join(str.split(self.status_msg['image_file'], '.')[-2:])
            key_name = '.'.join([self.status_msg['cloud_image_name'], suffix])
        else:
            key_name = path.basename(self.status_msg['image_file'])

        if not bucket_path:
            pass
        elif bucket_path[-1] == '/':
            key_name = ''.join([bucket_path, key_name])
        else:
            key_name = bucket_path

        try:
            statinfo = stat(self.status_msg['image_file'])
            self._image_size = statinfo.st_size

            client = get_client(
                's3', credentials['access_key_id'],
                credentials['secret_access_key'], None
            )

            client.upload_file(
                self.status_msg['image_file'],
                bucket_name,
                key_name,
                Callback=self._log_progress
            )

        except Exception as e:
            raise MashUploadException(
                'Raw upload to S3 bucket failed with: {0}'.format(e)
            )
