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
import lzma
from tempfile import NamedTemporaryFile

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.storage.blob.pageblobservice import PageBlobService

# project
from mash.services import get_configuration
from mash.services.uploader.cloud.base import UploadBase
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat
from mash.utils.filetype import FileType


class UploadAzure(UploadBase):
    """
    Implements system image upload to Azure

    Azure specific custom arguments:

    .. code:: python

        custom_args={
            'region': 'region_name',
            'container': 'storage_container_name',
            'storage_account': 'storage_account_name',
            'resource_group': 'optional_resource_group_name'
        }
    """
    def post_init(self):
        if not self.custom_args:
            self.custom_args = {}

        self.region = self.custom_args.get('region')
        if not self.region:
            raise MashUploadException(
                'required Azure region name for upload not specified'
            )

        self.container = self.custom_args.get('container')
        if not self.container:
            raise MashUploadException(
                'required Azure container name for upload not specified'
            )

        self.storage_account = self.custom_args.get('storage_account')
        if not self.storage_account:
            raise MashUploadException(
                'required Azure storage account name for upload not specified'
            )

        self.resource_group = self.custom_args.get('resource_group') or None

        self._create_auth_file()

        self.config = get_configuration(service='uploader')

    def upload(self):
        system_image_file_type = FileType(
            self.system_image_file
        )
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
        blob_name = ''.join([self.cloud_image_name, '.vhd'])

        if system_image_file_type.is_xz():
            open_image = lzma.LZMAFile
        else:
            open_image = open

        retries = self.config.get_azure_max_retry_attempts()
        while True:
            with open_image(self.system_image_file, 'rb') as image_stream:
                try:
                    page_blob_service.create_blob_from_stream(
                        self.container, blob_name, image_stream,
                        system_image_file_type.get_size(),
                        max_connections=self.config.get_azure_max_workers()
                    )
                    break
                except Exception as error:
                    msg = error
                    retries -= 1

            if retries < 1:
                raise MashUploadException(
                    'Unable to upload image: {0} to Azure: {1}'.format(
                        self.system_image_file,
                        msg
                    )
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
                            self.container, blob_name
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
