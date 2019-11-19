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

import adal
import copy
import json
import lzma
import re
import requests
import time

from datetime import date, datetime, timedelta

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import ContainerPermissions, PageBlobService

from mash.mash_exceptions import MashAzureUtilsException
from mash.utils.filetype import FileType
from mash.utils.mash_utils import create_json_file


def acquire_access_token(credentials, cloud_partner=False):
    """
    Get an access token from adal library.

    credentials:
      A service account json dictionary.
    """
    context = adal.AuthenticationContext(
        '/'.join([
            credentials['activeDirectoryEndpointUrl'],
            credentials['tenantId']
        ])
    )

    if cloud_partner:
        resource = 'https://cloudpartner.azure.com'
    else:
        resource = credentials['managementEndpointUrl']

    access_token = context.acquire_token_with_client_credentials(
        resource,
        credentials['clientId'],
        credentials['clientSecret']
    ).get('accessToken')

    return access_token


def copy_blob_to_classic_storage(
    auth_file, blob_name, source_container, source_resource_group,
    source_storage_account, destination_container, destination_resource_group,
    destination_storage_account
):
    """
    Copy a blob from ARM based storage account to a classic storage account.
    """
    source_page_blob_service = get_page_blob_service_with_account_keys(
        auth_file, source_storage_account, source_resource_group
    )

    source_blob_url = get_blob_url(
        source_page_blob_service, blob_name, source_container
    )

    page_blob_service = get_classic_page_blob_service(
        auth_file, destination_resource_group, destination_storage_account
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
            raise MashAzureUtilsException(
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
    page_blob_service = get_page_blob_service_with_account_keys(
        auth_file, storage_account, resource_group
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
    page_blob_service, blob_name, container,
    permissions=ContainerPermissions.READ, expire_hours=1, start_hours=0
):
    """
    Create a URL for the given blob with a shared access signature.

    The signature will expire based on expire_hours.
    """
    sas_token = page_blob_service.generate_container_shared_access_signature(
        container,
        permissions,
        datetime.utcnow() + timedelta(hours=expire_hours),
        datetime.utcnow() - timedelta(hours=start_hours)
    )

    source_blob_url = page_blob_service.make_blob_url(
        container,
        blob_name,
        sas_token=sas_token,
    )

    return source_blob_url


def get_page_blob_service_with_account_keys(
    auth_file,
    storage_account,
    resource_group
):
    """
    Return authenticated page blob service instance for the storage account.

    Using storage account keys.
    """
    storage_client = get_client_from_auth_file(
        StorageManagementClient,
        auth_path=auth_file
    )
    storage_key_list = storage_client.storage_accounts.list_keys(
        resource_group,
        storage_account
    )

    return PageBlobService(
        account_name=storage_account,
        account_key=storage_key_list.keys[0].value
    )


def get_page_blob_service_with_sas_token(storage_account, sas_token):
    """
    Return authenticated page blob service instance for the storage account.

    Using an sas token.
    """
    return PageBlobService(
        account_name=storage_account,
        sas_token=sas_token
    )


def get_classic_page_blob_service(auth_file, resource_group, storage_account):
    """
    Return authenticated page blob service instance for classic (ASM) account.
    """
    keys = get_classic_storage_account_keys(
        auth_file, resource_group, storage_account
    )

    page_blob_service = PageBlobService(
        account_name=storage_account,
        account_key=keys['primaryKey']
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

    access_token = acquire_access_token(credentials)
    headers = {'Authorization': 'Bearer ' + access_token}
    json_output = requests.post(endpoint, headers=headers).json()

    return json_output


def go_live_with_cloud_partner_offer(
    credentials, offer_id, publisher_id
):
    """
    Go live with cloud partner offer and return the operation location.
    """
    endpoint = get_cloud_partner_endpoint(
        offer_id,
        publisher_id,
        go_live=True
    )
    headers = get_cloud_partner_api_headers(
        credentials,
        content_type='application/json'
    )

    response = process_request(
        endpoint,
        headers,
        method='post',
        json_response=False
    )

    return response.headers['Location']


def get_cloud_partner_endpoint(
    offer_id, publisher_id, api_version='2017-10-31',
    publish=False, go_live=False
):
    """
    Return the endpoint URL to cloud partner API for offer and publisher.
    """
    endpoint = 'https://cloudpartner.azure.com/api/' \
               'publishers/{publisher_id}/' \
               'offers/{offer_id}' \
               '{method}' \
               '?api-version={api_version}'

    if publish:
        method = '/publish'
    elif go_live:
        method = '/golive'
    else:
        method = ''

    endpoint = endpoint.format(
        offer_id=offer_id,
        publisher_id=publisher_id,
        method=method,
        api_version=api_version
    )

    return endpoint


def get_cloud_partner_api_headers(
    credentials, content_type=None, if_match=None
):
    """
    Return dictionary of request headers for cloud partner API.
    """
    access_token = acquire_access_token(credentials, cloud_partner=True)

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + access_token
    }

    if content_type:
        headers['Content-Type'] = content_type

    if if_match:
        headers['If-Match'] = if_match

    return headers


def get_cloud_partner_operation_status(credentials, operation):
    """
    Get the status of the provided API operation.
    """
    endpoint = 'https://cloudpartner.azure.com{operation}'.format(
        operation=operation
    )

    headers = get_cloud_partner_api_headers(credentials)
    response = process_request(
        endpoint,
        headers
    )

    return response


def log_operation_response_status(response, log_callback):
    """
    Log the progress of the currently running operation step.
    """
    for step in response['steps']:
        if step['status'] == 'inProgress':
            log_callback(
                '{0} {1}% complete.'.format(
                    step['stepName'],
                    str(step['progressPercentage'])
                )
            )
            break


def put_cloud_partner_offer_doc(credentials, doc, offer_id, publisher_id):
    """
    Put an updated cloud partner offer doc to the API.
    """
    endpoint = get_cloud_partner_endpoint(
        offer_id,
        publisher_id
    )
    headers = get_cloud_partner_api_headers(
        credentials,
        content_type='application/json',
        if_match='*'
    )

    response = process_request(
        endpoint,
        headers,
        data=doc,
        method='put'
    )

    return response


def publish_cloud_partner_offer(
    credentials, emails, offer_id, publisher_id
):
    """
    Publish the cloud partner offer and return the operation location.
    """
    endpoint = get_cloud_partner_endpoint(
        offer_id,
        publisher_id,
        publish=True
    )
    headers = get_cloud_partner_api_headers(
        credentials,
        content_type='application/json'
    )

    response = process_request(
        endpoint,
        headers,
        data={'metadata': {'notification-emails': emails}},
        method='post',
        json_response=False
    )

    return response.headers['Location']


def process_request(
    endpoint, headers, data=None, method='get', json_response=True
):
    """
    Build and run API request.

    If the response code is not successful raise an exception for status.

    Return the response or json content.
    """
    kwargs = {
        'headers': headers
    }

    if data:
        kwargs['data'] = json.dumps(data)

    response = getattr(requests, method)(
        endpoint, **kwargs
    )

    if response.status_code not in (200, 202):
        response.raise_for_status()

    if json_response:
        return response.json()
    else:
        return response


def request_cloud_partner_offer_doc(credentials, offer_id, publisher_id):
    """
    Request a Cloud Partner Offer doc for the provided publisher and offer.

    credentials:
       A service account json dictionary.
    """
    endpoint = get_cloud_partner_endpoint(
        offer_id,
        publisher_id
    )
    headers = get_cloud_partner_api_headers(credentials)

    response = process_request(
        endpoint,
        headers,
        method='get'
    )

    return response


def update_cloud_partner_offer_doc(
    doc, blob_url, description, image_name, label, sku,
    vm_images_key='microsoft-azure-corevm.vmImagesPublicAzure',
    generation_id=None, cloud_image_name_generation_suffix=None
):
    """
    Update the cloud partner offer doc with a new version of the given sku.
    """
    matches = re.findall(r'\d{8}', image_name)

    # If image name already has a date use it as release date.
    if matches:
        release_date = datetime.strptime(matches[0], '%Y%m%d').date()
    else:
        release_date = date.today()

    version = {
        'osVhdUrl': blob_url,
        'label': label,
        'mediaName': image_name,
        'publishedDate': release_date.strftime("%m/%d/%Y"),
        'description': description,
        'showInGui': True,
        'lunVhdDetails': []
    }

    for doc_sku in doc['definition']['plans']:
        if doc_sku['planId'] == sku:
            release = release_date.strftime("%Y.%m.%d")

            if vm_images_key not in doc_sku:
                doc_sku[vm_images_key] = {}

            doc_sku[vm_images_key][release] = version

            if generation_id:
                for plan in doc_sku['diskGenerations']:
                    if plan['planId'] == generation_id:
                        generation_version = copy.deepcopy(version)
                        generation_version['mediaName'] = '-'.join([
                            image_name,
                            cloud_image_name_generation_suffix or generation_id
                        ])

                        if vm_images_key not in plan:
                            plan[vm_images_key] = {}

                        plan[vm_images_key][release] = generation_version
                        break

            break

    return doc


def deprecate_image_in_offer_doc(
    doc, image_name, sku, log_callback,
    vm_images_key='microsoft-azure-corevm.vmImagesPublicAzure'
):
    """
    Deprecate the image in the cloud partner offer doc.

    The image is set to not show in gui.
    """
    matches = re.findall(r'\d{8}', image_name)

    if matches:
        release_date = datetime.strptime(matches[0], '%Y%m%d').date()
        release = release_date.strftime("%Y.%m.%d")
    else:
        # image name must have a date to generate release key
        return doc

    for doc_sku in doc['definition']['plans']:
        if doc_sku['planId'] == sku \
                and doc_sku.get(vm_images_key) \
                and doc_sku[vm_images_key].get(release):

            image = doc_sku[vm_images_key][release]

            if image['mediaName'] == image_name:
                image['showInGui'] = False
            else:
                log_callback(
                    'Deprecation image name, {0} does match the mediaName '
                    'attribute, {1}.'.format(
                        image_name,
                        image['mediaName']
                    )
                )

            break

    return doc


def wait_on_cloud_partner_operation(
    credentials, operation, log_callback, wait_time=60 * 60 * 4
):
    """
    Wait for the cloud partner operation to finish.

    If the operation fails or is canceled an exception is raised.
    """
    while True:
        response = get_cloud_partner_operation_status(
            credentials, operation
        )
        status = response['status']

        if status == 'complete':
            return
        elif status in ('canceled', 'failed'):
            raise MashAzureUtilsException(
                'Cloud partner operation did not finish successfully.'
            )
        else:
            log_operation_response_status(response, log_callback)
            time.sleep(wait_time)


def upload_azure_image(
    blob_name,
    container,
    image_file,
    max_retry_attempts,
    max_workers,
    storage_account,
    result,
    credentials=None,
    resource_group=None,
    sas_token=None
):
    if sas_token:
        page_blob_service = get_page_blob_service_with_sas_token(
            storage_account,
            sas_token
        )
    elif credentials and resource_group:
        with create_json_file(credentials) as auth_file:
            page_blob_service = get_page_blob_service_with_account_keys(
                auth_file,
                storage_account,
                resource_group
            )
    else:
        raise MashAzureUtilsException(
            'Either an sas_token or credentials and resource_group '
            ' is required to upload an azure image to a page blob.'
        )

    system_image_file_type = FileType(image_file)
    if system_image_file_type.is_xz():
        open_image = lzma.LZMAFile
    else:
        open_image = open

    msg = ''
    while max_retry_attempts > 0:
        with open_image(image_file, 'rb') as image_stream:
            try:
                page_blob_service.create_blob_from_stream(
                    container,
                    blob_name,
                    image_stream,
                    system_image_file_type.get_size(),
                    max_connections=max_workers
                )
                return
            except Exception as error:
                msg = error
                max_retry_attempts -= 1

    result.put(
        'Unable to upload image: {0} to Azure: {1}'.format(
            image_file,
            msg
        )
    )
