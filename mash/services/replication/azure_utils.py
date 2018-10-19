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
import requests
import time

from datetime import datetime, timedelta

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import ContainerPermissions, PageBlobService

from mash.mash_exceptions import MashReplicationException


def copy_blob_to_classic_storage(
    auth_file, blob_name, source_container, source_resource_group,
    source_storage_account, destination_container, destination_resource_group,
    destination_storage_account, timeout=600
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

    start = time.time()
    end = start + timeout

    while time.time() < end:
        if copy.status == 'success':
            return
        else:
            time.sleep(30)

        copy = page_blob_service.get_blob_properties(
            destination_container,
            blob_name
        ).properties.copy

    raise MashReplicationException(
        'Time out waiting for async copy to complete. Copy may not have'
        ' completed successfully.'
    )


def get_blob_url(
    auth_file, blob_name, container, resource_group, storage_account,
    permissions=ContainerPermissions.READ, expire_hours=1
):
    """
    Create a URL for the given blob with a shared access signature.

    The storage account should be ARM based.

    The signature will expire based on expire_hours.
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
