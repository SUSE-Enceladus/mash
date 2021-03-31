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

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import (
    format_string_with_date,
    timestamp_from_epoch
)
from mash.services.status_levels import SUCCESS
from mash.utils.azure import (
    upload_azure_file,
    blob_exists,
    delete_blob
)


class AzureUploadJob(MashJob):
    """
    Implements VM image upload to Azure
    """
    def post_init(self):
        try:
            self.container = self.job_config['container']
            self.storage_account = self.job_config['storage_account']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'Azure upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.account = self.job_config.get('account')
        self.region = self.job_config.get('region')
        self.resource_group = self.job_config.get('resource_group')
        self.use_build_time = self.job_config.get('use_build_time')
        self.force_replace_image = self.job_config.get('force_replace_image')

    def run_job(self):
        self.status = SUCCESS
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
        blob_name = ''.join([self.cloud_image_name, '.vhd'])

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        exists = blob_exists(
            credentials,
            blob_name,
            self.container,
            self.resource_group,
            self.storage_account
        )

        if exists and not self.force_replace_image:
            raise MashUploadException(
                'Image tarball: {blob_name} already exists '
                'in container: {container}. Use force_replace_image '
                'to replace the existing tarball.'.format(
                    blob_name=blob_name,
                    container=self.container
                )
            )
        elif exists and self.force_replace_image:
            self.log_callback.info(
                'Deleting tarball: {0}, in the container named: '
                '{1}.'.format(
                    blob_name,
                    self.container
                )
            )
            delete_blob(
                credentials,
                blob_name,
                self.container,
                self.resource_group,
                self.storage_account
            )

        upload_azure_file(
            blob_name,
            self.container,
            self.status_msg['image_file'],
            self.storage_account,
            max_retry_attempts=self.config.get_azure_max_retry_attempts(),
            max_workers=self.config.get_azure_max_workers(),
            credentials=credentials,
            resource_group=self.resource_group,
            is_page_blob=True
        )

        self.status_msg['cloud_image_name'] = self.cloud_image_name
        self.status_msg['blob_name'] = blob_name
        self.log_callback.info(
            'Uploaded image: {0}, to the container: {1}'.format(
                blob_name,
                self.container
            )
        )
