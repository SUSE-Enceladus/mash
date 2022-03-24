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

from datetime import datetime, timedelta

from azure.identity import ClientSecretCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import (
    BlobServiceClient,
    generate_container_sas,
    ContainerSasPermissions
)


def create_sas_token(
    blob_service,
    storage_account,
    container,
    permissions=ContainerSasPermissions(read=True, list=True),
    expire_hours=1,
    start_hours=1
):
    expiry_time = datetime.utcnow() + timedelta(hours=expire_hours)
    start_time = datetime.utcnow() - timedelta(hours=start_hours)

    return generate_container_sas(
        storage_account,
        container,
        permission=permissions,
        expiry=expiry_time,
        start=start_time,
        account_key=blob_service.credential.account_key
    )


def get_blob_url(
    blob_service,
    blob_name,
    storage_account,
    container,
    permissions=ContainerSasPermissions(read=True, list=True),
    expire_hours=1,
    start_hours=1
):
    """
    Create a URL for the given blob with a shared access signature.

    The signature will expire based on expire_hours.
    """
    sas_token = create_sas_token(
        blob_service,
        storage_account,
        container,
        permissions=permissions,
        expire_hours=expire_hours,
        start_hours=start_hours
    )

    source_blob_url = (
        'https://{account}.blob.core.windows.net/'
        '{container}/{blob}?{token}'.format(
            account=storage_account,
            container=container,
            blob=blob_name,
            token=sas_token
        )
    )

    return source_blob_url


def get_storage_account_key(credentials, resource_group, storage_account):
    storage_client = get_client_from_json(
        StorageManagementClient,
        credentials
    )
    storage_key_list = storage_client.storage_accounts.list_keys(
        resource_group,
        storage_account
    )
    return storage_key_list.keys[0].value


def get_blob_service_with_account_keys(
    credentials,
    resource_group,
    storage_account
):
    """
    Return authenticated blob service instance for the storage account.

    Using storage account keys.
    """
    account_key = get_storage_account_key(
        credentials,
        resource_group,
        storage_account
    )

    return BlobServiceClient(
        account_url='https://{account_name}.blob.core.windows.net'.format(
            account_name=storage_account
        ),
        credential=account_key
    )


def get_blob_service_with_sas_token(
    storage_account,
    sas_token
):
    """
    Return authenticated page blob service instance for the storage account.

    Using an sas token.
    """
    return BlobServiceClient(
        account_url='https://{account_name}.blob.core.windows.net'.format(
            account_name=storage_account
        ),
        credential=sas_token
    )


def get_client_from_json(client, credentials):
    credential = get_secret_credential(credentials)
    return client(
        credential,
        credentials['subscriptionId']
    )


def get_secret_credential(credentials):
    return ClientSecretCredential(
        tenant_id=credentials['tenantId'],
        client_id=credentials['clientId'],
        client_secret=credentials['clientSecret']
    )
