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

from multiprocessing import Process, SimpleQueue
from tempfile import NamedTemporaryFile

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from mash.utils.azure import upload_azure_image


class AzureUploaderJob(MashJob):
    """
    Implements system image upload to Azure
    """
    def post_init(self):
        self._image_file = None
        self.source_regions = {}
        self.cloud_image_name = ''

        try:
            self.target_regions = self.job_config['target_regions']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'Azure uploader jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def run_job(self):
        self.status = SUCCESS
        self.send_log('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )

        for region, info in self.target_regions.items():
            account = info['account']
            self.request_credentials([account])
            credentials = self.credentials[account]
            blob_name = ''.join([self.cloud_image_name, '.vhd'])

            result = SimpleQueue()
            args = (
                blob_name,
                info['container'],
                credentials,
                self.image_file,
                self.config.get_azure_max_retry_attempts(),
                self.config.get_azure_max_workers(),
                info['resource_group'],
                info['storage_account'],
                result
            )
            upload_process = Process(
                target=upload_azure_image,
                args=args
            )
            upload_process.start()
            upload_process.join()

            if result.empty() is False:
                raise MashUploadException(result.get())

            self._create_auth_file(credentials)

            compute_client = get_client_from_auth_file(
                ComputeManagementClient, auth_path=self.auth_file.name
            )
            async_create_image = compute_client.images.create_or_update(
                info['resource_group'],
                self.cloud_image_name, {
                    'location': region,
                    'storage_profile': {
                        'os_disk': {
                            'os_type': 'Linux',
                            'os_state': 'Generalized',
                            'caching': 'ReadWrite',
                            'blob_uri': 'https://{0}.{1}/{2}/{3}'.format(
                                info['storage_account'],
                                'blob.core.windows.net',
                                info['container'],
                                blob_name
                            )
                        }
                    }
                }
            )
            async_create_image.wait()
            self.source_regions[region] = self.cloud_image_name
            self.send_log(
                'Uploaded image has ID: {0} in region {1}'.format(
                    self.cloud_image_name,
                    region
                )
            )

    def _create_auth_file(self, credentials):
        self.auth_file = NamedTemporaryFile()
        with open(self.auth_file.name, 'w') as azure_auth:
            azure_auth.write(JsonFormat.json_message(credentials))

    @property
    def image_file(self):
        """System image file property."""
        return self._image_file

    @image_file.setter
    def image_file(self, system_image_file):
        """
        Setter for image_file list.
        """
        self._image_file = system_image_file
