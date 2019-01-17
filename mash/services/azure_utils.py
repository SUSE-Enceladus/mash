# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

import adal
import json
import os
import requests
import time

from contextlib import contextmanager, suppress
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import ContainerPermissions, PageBlobService

from mash.mash_exceptions import MashReplicationException
from mash.utils.json_format import JsonFormat


def copy_blob_to_classic_storage(
    auth_file, blob_name, source_container, source_resource_group,
    source_storage_account, destination_container, destination_resource_group,
    destination_storage_account
):
    """
    Copy a blob from ARM based storage account to a classic storage account.
    """
    source_blob_url = get_blob_url(
        auth_file, blob_name, source_container, source_resource_group,
        source_storage_account
    )

    destination_keys = get_classic_storage_account_keys(
        auth_file, destination_resource_group, destination_storage_account
    )

    page_blob_service = PageBlobService(
        account_name=destination_storage_account,
        account_key=destination_keys['primaryKey']
    )

    copy = page_blob_service.copy_blob(
        destination_container,
        blob_name,
        source_blob_url
    )

    while True:
        if copy.status == 'success':
            return
        elif copy.status == 'failed':
            raise MashReplicationException(
                'Azure blob copy failed.'
            )
        else:
            time.sleep(60)
            copy = page_blob_service.get_blob_properties(
                destination_container,
                blob_name
            ).properties.copy


def delete_page_blob(
    auth_file, blob, container, resource_group, storage_account
):
    """
    Delete page blob in container.
    """
    page_blob_service = get_page_blob_service(
        auth_file, resource_group, storage_account
    )
    page_blob_service.delete_blob(container, blob)


def delete_image(auth_file, resoure_group, image_name):
    """
    Delete the image from resource group.
    """
    compute_client = get_client_from_auth_file(
        ComputeManagementClient, auth_path=auth_file
    )
    async_delete_image = compute_client.images.delete(
        resoure_group, image_name
    )
    async_delete_image.wait()


def get_blob_url(
    auth_file, blob_name, container, resource_group, storage_account,
    permissions=ContainerPermissions.READ, expire_hours=1
):
    """
    Create a URL for the given blob with a shared access signature.

    The storage account should be ARM based.

    The signature will expire based on expire_hours.
    """
    page_blob_service = get_page_blob_service(
        auth_file, resource_group, storage_account
    )

    sas_token = page_blob_service.generate_container_shared_access_signature(
        container,
        permissions,
        datetime.utcnow() + timedelta(hours=expire_hours)
    )

    source_blob_url = page_blob_service.make_blob_url(
        container,
        blob_name,
        sas_token=sas_token,
    )

    return source_blob_url


def get_page_blob_service(auth_file, resource_group, storage_account):
    """
    Return authenticated page blob service instance for the storage account.
    """
    storage_client = get_client_from_auth_file(
        StorageManagementClient,
        auth_path=auth_file
    )
    storage_key_list = storage_client.storage_accounts.list_keys(
        resource_group, storage_account
    )
    page_blob_service = PageBlobService(
        account_name=storage_account,
        account_key=storage_key_list.keys[0].value
    )

    return page_blob_service


def get_classic_storage_account_keys(
    auth_file, resource_group, storage_account, api_version='2016-11-01'
):
    """
    Acquire classic storage account keys using service account credentials.
    """
    with open(auth_file) as sa_file:
        credentials = json.load(sa_file)

    # get an Azure access token using the adal library
    context = adal.AuthenticationContext(
        '/'.join([
            credentials['activeDirectoryEndpointUrl'],
            credentials['tenantId']
        ])
    )
    access_token = context.acquire_token_with_client_credentials(
        credentials['managementEndpointUrl'],
        credentials['clientId'],
        credentials['clientSecret']
    ).get('accessToken')

    url = '{resource_url}subscriptions/' \
          '{subscription_id}/resourceGroups/{resource_group}/' \
          'providers/Microsoft.ClassicStorage/storageAccounts/' \
          '{storage_account}/listKeys?api-version={api_version}'

    endpoint = url.format(
        resource_url=credentials['resourceManagerEndpointUrl'],
        subscription_id=credentials['subscriptionId'],
        resource_group=resource_group,
        storage_account=storage_account,
        api_version=api_version
    )

    headers = {'Authorization': 'Bearer ' + access_token}
    json_output = requests.post(endpoint, headers=headers).json()

    return json_output


@contextmanager
def create_auth_file(credentials):
    try:
        auth_file = NamedTemporaryFile(delete=False)
        with open(auth_file.name, 'w') as azure_auth:
            azure_auth.write(JsonFormat.json_message(credentials))
        yield auth_file.name
    finally:
        with suppress(OSError):
            os.remove(auth_file.name)
