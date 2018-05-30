# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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
from tempfile import NamedTemporaryFile

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.storage.blob.pageblobservice import PageBlobService

# project
from mash.services.uploader.cloud.base import UploadBase
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat


class UploadAzure(UploadBase):
    """
    Implements system image upload to Azure
    """
    def post_init(self):
        if not self.custom_args:
            self.custom_args = {}

        if 'region' in self.custom_args:
            self.region = self.custom_args['region']
        else:
            raise MashUploadException(
                'required Azure region name for upload not specified'
            )

        if 'container_name' in self.custom_args:
            self.container_name = self.custom_args['container_name']
        else:
            raise MashUploadException(
                'required Azure container name for upload not specified'
            )

        if 'storage_account' in self.custom_args:
            self.storage_account = self.custom_args['storage_account']
        else:
            raise MashUploadException(
                'required Azure storage account name for upload not specified'
            )

        self.resource_group = None
        if 'resource_group' in self.custom_args:
            self.resource_group = self.custom_args['resource_group']

        self._create_auth_file()

    def upload(self):
        storage_client = get_client_from_auth_file(
            StorageManagementClient, auth_path=self.auth_file.name
        )
        storage_key_list = storage_client.storage_accounts.list_keys(
            self.resource_group, self.storage_account
        )
        page_blob_service = PageBlobService(
            account_name=self.storage_account,
            account_key=storage_key_list.keys[0].value
        )
        page_blob_service.create_blob_from_path(
            self.container_name, self.cloud_image_name, self.system_image_file
        )
        compute_client = get_client_from_auth_file(
            ComputeManagementClient, auth_path=self.auth_file.name
        )
        async_create_image = compute_client.images.create_or_update(
            self.resource_group,
            self.cloud_image_name, {
                'location': self.region,
                'storage_profile': {
                    'os_disk': {
                        'os_type': 'Linux',
                        'os_state': 'Generalized',
                        'caching': 'ReadWrite',
                        'blob_uri': 'https://{0}.{1}/{2}/{3}'.format(
                            self.storage_account, 'blob.core.windows.net',
                            self.container_name, self.cloud_image_name
                        )
                    }
                }
            }
        )
        async_create_image.wait()
        return self.cloud_image_name, self.region

    def _create_auth_file(self):
        self.auth_file = NamedTemporaryFile()
        with open(self.auth_file.name, 'w') as azure_auth:
            azure_auth.write(JsonFormat.json_message(self.credentials))
