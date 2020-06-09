# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

from os import stat

from oci.object_storage import ObjectStorageClient, UploadManager

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS


class OCIUploadJob(MashJob):
    """
    Implements VM image upload to OCI
    """
    def post_init(self):
        self._image_size = 0
        self._total_bytes_transferred = 0
        self._next_percent = 0
        self._progress_step = 20

        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.oci_user_id = self.job_config['oci_user_id']
            self.tenancy = self.job_config['tenancy']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'OCI upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.upload_process_count = self.config.get_oci_upload_process_count()

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        config = {
            'user': self.oci_user_id,
            'key_content': credentials['signing_key'],
            'fingerprint': credentials['fingerprint'],
            'tenancy': self.tenancy,
            'region': self.region
        }
        object_storage = ObjectStorageClient(config)
        namespace = object_storage.get_namespace().data
        upload_manager = UploadManager(
            object_storage,
            allow_parallel_uploads=True,
            parallel_process_count=self.upload_process_count
        )

        object_name = ''.join([self.cloud_image_name, '.qcow2'])
        self._image_size = stat(self.image_file).st_size

        with open(self.image_file, 'rb') as image_stream:
            upload_manager.upload_stream(
                namespace,
                self.bucket,
                object_name,
                image_stream,
                progress_callback=self._progress_callback
            )

        self.source_regions = {
            'cloud_image_name': self.cloud_image_name,
            'object_name': object_name,
            'namespace': namespace
        }
        self.log_callback.info(
            'Uploaded image: {0}, to the bucket named: {1}'.format(
                object_name,
                self.bucket
            )
        )

    def _progress_callback(self, bytes_uploaded):
        self._total_bytes_transferred += bytes_uploaded
        percent_transferred = (self._total_bytes_transferred * 100) / self._image_size

        if percent_transferred >= self._next_percent:
            current_percent = int(
                percent_transferred - (percent_transferred % self._progress_step)
            )
            self.log_callback.info('Image {progress}% uploaded.'.format(
                progress=str(current_percent)
            ))
            self._next_percent += self._progress_step
