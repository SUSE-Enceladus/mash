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

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date, create_json_file
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
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.container = self.job_config['container']
            self.resource_group = self.job_config['resource_group']
            self.storage_account = self.job_config['storage_account']
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

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]
        blob_name = ''.join([self.cloud_image_name, '.vhd'])

        result = SimpleQueue()
        args = (
            blob_name,
            self.container,
            credentials,
            self.image_file,
            self.config.get_azure_max_retry_attempts(),
            self.config.get_azure_max_workers(),
            self.resource_group,
            self.storage_account,
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

        with create_json_file(credentials) as auth_file:
            compute_client = get_client_from_auth_file(
                ComputeManagementClient, auth_path=auth_file
            )
            async_create_image = compute_client.images.create_or_update(
                self.resource_group,
                self.cloud_image_name, {
                    'location': self.region,
                    'hyper_vgeneration': 'V1',
                    'storage_profile': {
                        'os_disk': {
                            'os_type': 'Linux',
                            'os_state': 'Generalized',
                            'caching': 'ReadWrite',
                            'blob_uri': 'https://{0}.{1}/{2}/{3}'.format(
                                self.storage_account,
                                'blob.core.windows.net',
                                self.container,
                                blob_name
                            )
                        }
                    }
                }
            )
            async_create_image.wait()

        self.source_regions[self.region] = self.cloud_image_name
        self.send_log(
            'Uploaded image has ID: {0} in region {1}'.format(
                self.cloud_image_name,
                self.region
            )
        )

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
