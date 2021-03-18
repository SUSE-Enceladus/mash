# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import (
    format_string_with_date,
    timestamp_from_epoch
)
from mash.services.status_levels import SUCCESS
from aliyun_img_utils.aliyun_image import AliyunImage


class AliyunUploadJob(MashJob):
    """
    Implements system image upload to Aliyun
    """
    def post_init(self):
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'Aliyun upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.use_build_time = self.job_config.get('use_build_time')
        self.force_replace_image = self.job_config.get('force_replace_image')

        # How often to update log callback with download progress.
        # 25 updates every 25%. I.e. 25, 50, 75, 100.
        self.download_progress_percent = 25
        self.percent_uploaded = 0
        self.progress_log = {}

    def run_job(self):
        self.status = SUCCESS
        self.percent_uploaded = 0
        self.progress_log = {}
        self.log_callback.info('Uploading image.')

        timestamp = None
        build_time = self.status_msg.get('build_time', 'unknown')

        if self.use_build_time and (build_time != 'unknown'):
            timestamp = timestamp_from_epoch(build_time)
        elif self.use_build_time and (build_time == 'unknown'):
            raise MashUploadException(
                'use_build_time set for job but build time is unknown.'
            )

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name,
            timestamp=timestamp
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        aliyun_image = AliyunImage(
            credentials['access_key'],
            credentials['access_secret'],
            self.region,
            self.bucket,
            log_callback=self.log_callback
        )

        object_name = ''.join([self.cloud_image_name, '.qcow2'])

        exists = aliyun_image.image_tarball_exists(object_name)
        if exists and not self.force_replace_image:
            raise MashUploadException(
                'Image: {object_name} already exists '
                'in bucket: {bucket}. Use force_replace_image '
                'to replace the existing tarball.'.format(
                    object_name=object_name,
                    bucket=self.bucket
                )
            )
        elif exists and self.force_replace_image:
            self.log_callback.info(
                'Deleting image file: {0}, in the bucket named: {1}'.format(
                    object_name,
                    self.bucket
                )
            )
            aliyun_image.delete_storage_blob(object_name)

        aliyun_image.upload_image_tarball(
            self.status_msg['image_file'],
            blob_name=object_name,
            progress_callback=self.progress_callback
        )

        self.status_msg['cloud_image_name'] = self.cloud_image_name
        self.status_msg['object_name'] = object_name
        self.log_callback.info(
            'Uploaded image: {0}, to the bucket named: {1}'.format(
                object_name,
                self.bucket
            )
        )

    def progress_callback(self, read_size, total_size, done=False):
        """
        Update progress in log callback
        """
        if done:
            self.log_callback.info('Image download finished.')
        else:
            self.percent_uploaded += int(((read_size) / total_size) * 100)

            if self.percent_uploaded % self.download_progress_percent == 0 \
                    and self.percent_uploaded not in self.progress_log:
                self.log_callback.info(
                    f'Image {str(self.percent_uploaded)}% downloaded.'
                )
                self.progress_log[self.percent_uploaded] = True
