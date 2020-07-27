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
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from mash.utils.azure import upload_azure_file


class AzureUploadJob(MashJob):
    """
    Implements VM image upload to Azure
    """
    def post_init(self):
        try:
            self.container = self.job_config['container']
            self.storage_account = self.job_config['storage_account']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
            self.account = self.job_config.get('account')
            self.region = self.job_config.get('region')
            self.resource_group = self.job_config.get('resource_group')
        except KeyError as error:
            raise MashUploadException(
                'Azure upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )
        blob_name = ''.join([self.cloud_image_name, '.vhd'])

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        upload_azure_file(
            blob_name,
            self.container,
            self.status_msg['image_file'],
            self.config.get_azure_max_retry_attempts(),
            self.config.get_azure_max_workers(),
            self.storage_account,
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
