import json

from datetime import date
from pytest import raises
from unittest.mock import MagicMock, patch
from collections import namedtuple
from multiprocessing import SimpleQueue

from azure.mgmt.storage import StorageManagementClient
from mash.mash_exceptions import MashAzureUtilsException
from mash.services.azure_utils import (
    acquire_access_token,
    delete_image,
    delete_page_blob,
    deprecate_image_in_offer_doc,
    get_classic_storage_account_keys,
    get_blob_url,
    go_live_with_cloud_partner_offer,
    copy_blob_to_classic_storage,
    get_page_blob_service,
    get_classic_page_blob_service,
    log_operation_response_status,
    publish_cloud_partner_offer,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc,
    update_cloud_partner_offer_doc,
    wait_on_cloud_partner_operation,
    upload_azure_image
)


@patch('mash.services.azure_utils.adal')
def test_acquire_access_token(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    acquire_access_token(credentials)

    mock_adal.AuthenticationContext.assert_called_once_with(
        'https://login.microsoftonline.com/'
        '09876543-1234-1234-1234-123456789012'
    )
    context.acquire_token_with_client_credentials.assert_called_once_with(
        'https://management.core.windows.net/',
        '09876543-1234-1234-1234-123456789012',
        '09876543-1234-1234-1234-123456789012'
    )


@patch('mash.services.azure_utils.adal')
def test_acquire_access_token_cloud_partner(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    acquire_access_token(credentials, cloud_partner=True)

    mock_adal.AuthenticationContext.assert_called_once_with(
        'https://login.microsoftonline.com/'
        '09876543-1234-1234-1234-123456789012'
    )
    context.acquire_token_with_client_credentials.assert_called_once_with(
        'https://cloudpartner.azure.com',
        '09876543-1234-1234-1234-123456789012',
        '09876543-1234-1234-1234-123456789012'
    )


@patch('mash.services.azure_utils.acquire_access_token')
@patch('mash.services.azure_utils.requests')
def test_get_classic_storage_account_keys(
    mock_requests, mock_acquire_access_token
):
    mock_acquire_access_token.return_value = '1234567890'
    response = MagicMock()
    response.json.return_value = {'primaryKey': '123', 'secondaryKey': '321'}
    mock_requests.post.return_value = response

    keys = get_classic_storage_account_keys(
        '../data/azure_creds.json', 'rg1', 'sa1'
    )

    assert keys['primaryKey'] == '123'
    assert keys['secondaryKey'] == '321'


def test_get_blob_url():
    page_blob_service = MagicMock()
    page_blob_service.generate_container_shared_access_signature \
        .return_value = 'token123'
    page_blob_service.make_blob_url.return_value = 'https://test/url/?token123'

    url = get_blob_url(
        page_blob_service, 'blob1', 'container1'
    )

    assert url == 'https://test/url/?token123'
    page_blob_service.make_blob_url.assert_called_once_with(
        'container1',
        'blob1',
        sas_token='token123'
    )


@patch('mash.services.azure_utils.get_client_from_auth_file')
@patch('mash.services.azure_utils.PageBlobService')
def test_get_page_blob_service(
    mock_page_blob_service, mock_get_client_from_auth
):
    storage_client = MagicMock()
    mock_get_client_from_auth.return_value = storage_client

    key1 = MagicMock()
    key1.value = '12345678'
    key2 = MagicMock()
    key2.value = '87654321'
    key_list = MagicMock()
    key_list.keys = [key1, key2]
    storage_client.storage_accounts.list_keys.return_value = key_list

    page_blob_service = MagicMock()
    mock_page_blob_service.return_value = page_blob_service

    service = get_page_blob_service(
        '../data/azure_creds.json', 'rg1', 'sa1'
    )

    assert service == page_blob_service
    storage_client.storage_accounts.list_keys.assert_called_once_with(
        'rg1', 'sa1'
    )
    mock_page_blob_service.assert_called_once_with(
        account_name='sa1', account_key='12345678'
    )


@patch('mash.services.azure_utils.get_classic_storage_account_keys')
@patch('mash.services.azure_utils.PageBlobService')
def test_get_classic_page_blob_service(
    mock_page_blob_service, mock_get_classic_storage_account_keys
):
    keys = {'primaryKey': '12345678'}
    mock_get_classic_storage_account_keys.return_value = keys

    page_blob_service = MagicMock()
    mock_page_blob_service.return_value = page_blob_service

    service = get_classic_page_blob_service(
        '../data/azure_creds.json', 'rg1', 'sa1'
    )

    assert service == page_blob_service
    mock_page_blob_service.assert_called_once_with(
        account_name='sa1', account_key='12345678'
    )


@patch('mash.services.azure_utils.get_blob_url')
@patch('mash.services.azure_utils.get_page_blob_service')
@patch('mash.services.azure_utils.get_classic_page_blob_service')
@patch('mash.services.azure_utils.time.sleep')
def test_copy_blob_to_classic_storage(
    mock_time, mock_get_classic_page_blob_service,
    mock_get_page_blob_service, mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'

    copy = MagicMock()
    copy.status = 'pending'

    props_copy = MagicMock()
    props_copy.properties.copy.status = 'success'

    page_blob_service = MagicMock()
    page_blob_service.copy_blob.return_value = copy
    page_blob_service.get_blob_properties.return_value = props_copy
    mock_get_classic_page_blob_service.return_value = page_blob_service

    mock_get_page_blob_service.return_value = page_blob_service

    copy_blob_to_classic_storage(
        '../data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
        'dc2', 'drg2', 'dsa2'
    )

    mock_get_blob_url.assert_called_once_with(
        page_blob_service, 'blob1', 'sc1'
    )


@patch('mash.services.azure_utils.get_blob_url')
@patch('mash.services.azure_utils.get_page_blob_service')
@patch('mash.services.azure_utils.get_classic_page_blob_service')
def test_copy_blob_to_classic_storage_failed(
    mock_get_classic_page_blob_service, mock_get_page_blob_service,
    mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'

    copy = MagicMock()
    copy.status = 'failed'

    page_blob_service = MagicMock()
    page_blob_service.copy_blob.return_value = copy
    mock_get_classic_page_blob_service.return_value = page_blob_service

    with raises(MashAzureUtilsException) as error:
        copy_blob_to_classic_storage(
            '../data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
            'dc2', 'drg2', 'dsa2'
        )

    assert str(error.value) == 'Azure blob copy failed.'


@patch('mash.services.azure_utils.get_page_blob_service')
def test_delete_page_blob(mock_get_page_blob_service):
    page_blob_service = MagicMock()
    mock_get_page_blob_service.return_value = page_blob_service

    delete_page_blob(
        '../data/azure_creds.json', 'blob1', 'container1', 'rg1', 'sa1'
    )

    page_blob_service.delete_blob.assert_called_once_with(
        'container1',
        'blob1'
    )


@patch('mash.services.azure_utils.get_client_from_auth_file')
def test_delete_image(mock_get_client):
    compute_client = MagicMock()
    async_wait = MagicMock()
    compute_client.images.delete.return_value = async_wait
    mock_get_client.return_value = compute_client

    delete_image(
        '../data/azure_creds.json', 'rg1', 'image123'
    )
    compute_client.images.delete.assert_called_once_with(
        'rg1', 'image123'
    )
    async_wait.wait.assert_called_once_with()


@patch('mash.services.azure_utils.requests')
@patch('mash.services.azure_utils.acquire_access_token')
def test_go_live_with_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    response = go_live_with_cloud_partner_offer(
        credentials, 'sles', 'suse'
    )

    assert response == '/api/endpoint/url'


@patch('mash.services.azure_utils.requests')
@patch('mash.services.azure_utils.acquire_access_token')
def test_publish_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    response = publish_cloud_partner_offer(
        credentials, 'jdoe@fake.com', 'sles', 'suse'
    )

    assert response == '/api/endpoint/url'


def test_log_operation_response_status():
    callback = MagicMock()
    response = {
        'steps': [{
            'status': 'inProgress',
            'stepName': 'Publishing the image',
            'progressPercentage': 30
        }]
    }

    log_operation_response_status(response, callback)
    callback.assert_called_once_with(
        'Publishing the image 30% complete.'
    )


@patch('mash.services.azure_utils.requests')
@patch('mash.services.azure_utils.acquire_access_token')
def test_put_cloud_partner_offer_doc(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'response': 'doc'}
    mock_requests.put.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    request_doc = {'test': 'doc'}

    response = put_cloud_partner_offer_doc(
        credentials, request_doc, 'sles', 'suse'
    )

    assert response['response'] == 'doc'


@patch('mash.services.azure_utils.acquire_access_token')
@patch('mash.services.azure_utils.requests')
def test_request_cloud_partner_offer_doc(
    mock_requests, mock_acquire_access_token
):
    mock_acquire_access_token.return_value = '1234567890'
    response = MagicMock()
    response.json.return_value = {'offer': 'doc'}
    mock_requests.get.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    request_cloud_partner_offer_doc(
        credentials, 'sles', 'suse',
    )
    mock_requests.get.assert_called_once_with(
        'https://cloudpartner.azure.com/api/publishers/suse/'
        'offers/sles?api-version=2017-10-31',
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer 1234567890'
        }
    )


def test_update_cloud_partner_offer_doc():
    today = date.today()
    release = today.strftime("%Y.%m.%d")
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'

    doc = {
        'definition': {
            'plans': [
                {'planId': '123'}
            ]
        }
    }

    doc = update_cloud_partner_offer_doc(
        doc,
        'blob/url/.vhd',
        'New image for v123',
        'New Image',
        'New Image 123',
        '123'
    )

    assert doc['definition']['plans'][0][vm_images_key][release]['label'] == \
        'New Image 123'


def test_update_cloud_partner_offer_doc_existing_date():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'

    doc = {
        'definition': {
            'plans': [
                {'planId': '123'}
            ]
        }
    }

    doc = update_cloud_partner_offer_doc(
        doc,
        'blob/url/.vhd',
        'New image for v123',
        'New Image 20180909',
        'New Image 123',
        '123'
    )

    label = doc['definition']['plans'][0][vm_images_key]['2018.09.09']['label']
    assert label == 'New Image 123'


@patch('mash.services.azure_utils.log_operation_response_status')
@patch('mash.services.azure_utils.time')
@patch('mash.services.azure_utils.acquire_access_token')
@patch('mash.services.azure_utils.requests')
def test_wait_on_cloud_partner_operation(
    mock_requests, mock_acquire_access_token, mock_time,
    mock_log_operation
):
    mock_acquire_access_token.return_value = '1234567890'
    callback = MagicMock()
    response = MagicMock()
    response.json.side_effect = [
        {'status': 'running'},
        {'status': 'complete'}
    ]
    mock_requests.get.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    wait_on_cloud_partner_operation(
        credentials, '/api/test/operation', callback
    )


@patch('mash.services.azure_utils.time')
@patch('mash.services.azure_utils.acquire_access_token')
@patch('mash.services.azure_utils.requests')
def test_wait_on_cloud_partner_operation_failed(
    mock_requests, mock_acquire_access_token, mock_time
):
    mock_acquire_access_token.return_value = '1234567890'
    callback = MagicMock()
    response = MagicMock()
    response.json.return_value = {'status': 'failed'}
    mock_requests.get.return_value = response

    with open('../data/azure_creds.json') as f:
        credentials = json.load(f)

    with raises(MashAzureUtilsException) as error:
        wait_on_cloud_partner_operation(
            credentials, '/api/test/operation', callback
        )

    assert str(error.value) == \
        'Cloud partner operation did not finish successfully.'


def test_deprecate_image_in_offer():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'
    callback = MagicMock()

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123',
                    vm_images_key: {
                        '2018.09.09': {
                            'label': 'New Image 20180909',
                            'mediaName': 'new_image_20180909'
                        }
                    }
                }
            ]
        }
    }

    doc = deprecate_image_in_offer_doc(
        doc,
        'new_image_20180909',
        '123',
        callback
    )

    release = doc['definition']['plans'][0][vm_images_key]['2018.09.09']
    assert release['showInGui'] is False


def test_deprecate_image_in_offer_invalid():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'
    callback = MagicMock()

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123'
                }
            ]
        }
    }

    deprecate_image_in_offer_doc(
        doc,
        'new_image',
        '123',
        callback
    )

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123',
                    vm_images_key: {
                        '2018.09.09': {
                            'label': 'New Image 20180909',
                            'mediaName': 'new_image'
                        }
                    }
                }
            ]
        }
    }

    deprecate_image_in_offer_doc(
        doc,
        'new_image_20180909',
        '123',
        callback
    )

    callback.assert_called_once_with(
        'Deprecation image name, new_image_20180909 does match the '
        'mediaName attribute, new_image.'
    )


@patch('builtins.open')
@patch('mash.services.azure_utils.create_json_file')
@patch('mash.services.azure_utils.get_client_from_auth_file')
@patch('mash.services.azure_utils.PageBlobService')
@patch('mash.services.azure_utils.FileType')
@patch('mash.services.azure_utils.lzma')
def test_upload_azure_image(
    mock_lzma,
    mock_FileType,
    mock_PageBlobService,
    mock_get_client_from_auth_file,
    mock_create_json_file,
    mock_open
):
    creds_handle = MagicMock()
    creds_handle.__enter__.return_value = 'tempfile'
    mock_create_json_file.return_value = creds_handle

    lzma_handle = MagicMock()
    lzma_handle.__enter__.return_value = lzma_handle
    mock_lzma.LZMAFile.return_value = lzma_handle

    open_handle = MagicMock()
    open_handle.__enter__.return_value = open_handle
    mock_open.return_value = open_handle

    client = MagicMock()
    mock_get_client_from_auth_file.return_value = client

    page_blob_service = MagicMock()
    mock_PageBlobService.return_value = page_blob_service

    key_type = namedtuple('key_type', ['value', 'key_name'])
    async_create_image = MagicMock()
    storage_key_list = MagicMock()
    storage_key_list.keys = [
        key_type(value='key', key_name='key_name')
    ]

    client.storage_accounts.list_keys.return_value = storage_key_list
    client.images.create_or_update.return_value = async_create_image

    system_image_file_type = MagicMock()
    system_image_file_type.get_size.return_value = 1024
    system_image_file_type.is_xz.return_value = True
    mock_FileType.return_value = system_image_file_type

    credentials = {
        'clientId': 'a',
        'clientSecret': 'b',
        'subscriptionId': 'c',
        'tenantId': 'd',
        'activeDirectoryEndpointUrl': 'https://login.microsoftonline.com',
        'resourceManagerEndpointUrl': 'https://management.azure.com/',
        'activeDirectoryGraphResourceId': 'https://graph.windows.net/',
        'sqlManagementEndpointUrl':
            'https://management.core.windows.net:8443/',
        'galleryEndpointUrl': 'https://gallery.azure.com/',
        'managementEndpointUrl': 'https://management.core.windows.net/'
    }

    result = SimpleQueue()
    args = (
        'name.vhd',
        'container',
        credentials,
        'file.vhdfixed.xz',
        5,
        8,
        'group_name',
        'storage',
        result
    )
    upload_azure_image(*args)
    assert result.empty()

    mock_get_client_from_auth_file.assert_called_once_with(
        StorageManagementClient,
        auth_path='tempfile'
    )
    client.storage_accounts.list_keys.assert_called_once_with(
        'group_name', 'storage'
    )
    mock_PageBlobService.assert_called_once_with(
        account_key='key', account_name='storage'
    )
    mock_FileType.assert_called_once_with('file.vhdfixed.xz')
    system_image_file_type.is_xz.assert_called_once_with()
    page_blob_service.create_blob_from_stream.assert_called_once_with(
        'container', 'name.vhd', lzma_handle, 1024,
        max_connections=8
    )

    system_image_file_type.is_xz.return_value = False
    page_blob_service.create_blob_from_stream.side_effect = Exception

    upload_azure_image(*args)
    assert result.empty() is False
