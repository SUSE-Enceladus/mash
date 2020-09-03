import json

from datetime import date
from pytest import raises
from unittest.mock import MagicMock, patch
from collections import namedtuple

from azure.mgmt.storage import StorageManagementClient
from mash.mash_exceptions import MashAzureUtilsException
from mash.utils.azure import (
    acquire_access_token,
    delete_image,
    delete_blob,
    deprecate_image_in_offer_doc,
    get_classic_storage_account_keys,
    get_blob_url,
    go_live_with_cloud_partner_offer,
    copy_blob_to_classic_storage,
    get_blob_service_with_account_keys,
    get_classic_blob_service,
    log_operation_response_status,
    publish_cloud_partner_offer,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc,
    update_cloud_partner_offer_doc,
    wait_on_cloud_partner_operation,
    upload_azure_file,
    get_blob_service_with_sas_token
)


@patch('mash.utils.azure.adal')
def test_acquire_access_token(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('test/data/azure_creds.json') as f:
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


@patch('mash.utils.azure.adal')
def test_acquire_access_token_cloud_partner(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('test/data/azure_creds.json') as f:
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


@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_get_classic_storage_account_keys(
    mock_requests, mock_acquire_access_token
):
    mock_acquire_access_token.return_value = '1234567890'
    response = MagicMock()
    response.json.return_value = {'primaryKey': '123', 'secondaryKey': '321'}
    mock_requests.post.return_value = response

    keys = get_classic_storage_account_keys(
        'test/data/azure_creds.json', 'rg1', 'sa1'
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


@patch('mash.utils.azure.get_client_from_auth_file')
@patch('mash.utils.azure.BlockBlobService')
@patch('mash.utils.azure.PageBlobService')
def test_get_blob_service_with_account_keys(
    mock_page_blob_service, mock_block_blob_service,
    mock_get_client_from_auth
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

    blob_service = MagicMock()
    mock_page_blob_service.return_value = blob_service
    mock_block_blob_service.return_value = blob_service

    service = get_blob_service_with_account_keys(
        'test/data/azure_creds.json', 'sa1', 'rg1', is_page_blob=True
    )

    assert service == blob_service
    storage_client.storage_accounts.list_keys.assert_called_once_with(
        'rg1', 'sa1'
    )
    mock_page_blob_service.assert_called_once_with(
        account_name='sa1', account_key='12345678'
    )

    service = get_blob_service_with_account_keys(
        'test/data/azure_creds.json', 'sa1', 'rg1'
    )
    assert service == blob_service


@patch('mash.utils.azure.get_classic_storage_account_keys')
@patch('mash.utils.azure.BlockBlobService')
@patch('mash.utils.azure.PageBlobService')
def test_get_classic_blob_service(
    mock_page_blob_service, mock_block_blob_service,
    mock_get_classic_storage_account_keys
):
    keys = {'primaryKey': '12345678'}
    mock_get_classic_storage_account_keys.return_value = keys

    blob_service = MagicMock()
    mock_page_blob_service.return_value = blob_service
    mock_block_blob_service.return_value = blob_service

    service = get_classic_blob_service(
        'test/data/azure_creds.json', 'rg1', 'sa1', is_page_blob=True
    )

    assert service == blob_service
    mock_page_blob_service.assert_called_once_with(
        account_name='sa1', account_key='12345678'
    )

    service = get_classic_blob_service(
        'test/data/azure_creds.json', 'rg1', 'sa1'
    )

    assert service == blob_service

    # Error
    keys = {'error': {'some': 'data'}}
    mock_get_classic_storage_account_keys.return_value = keys

    with raises(MashAzureUtilsException):
        get_classic_blob_service(
            'test/data/azure_creds.json', 'rg1', 'sa1'
        )


@patch('mash.utils.azure.get_blob_url')
@patch('mash.utils.azure.get_blob_service_with_account_keys')
@patch('mash.utils.azure.get_classic_blob_service')
@patch('mash.utils.azure.time.sleep')
def test_copy_blob_to_classic_storage(
    mock_time, mock_get_classic_blob_service,
    mock_get_blob_service, mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'

    copy = MagicMock()
    copy.status = 'pending'

    props_copy = MagicMock()
    props_copy.properties.copy.status = 'success'

    blob_service = MagicMock()
    blob_service.copy_blob.return_value = copy
    blob_service.get_blob_properties.return_value = props_copy
    mock_get_classic_blob_service.return_value = blob_service

    mock_get_blob_service.return_value = blob_service

    copy_blob_to_classic_storage(
        'test/data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
        'dc2', 'drg2', 'dsa2', is_page_blob=True
    )

    mock_get_blob_url.assert_called_once_with(
        blob_service, 'blob1', 'sc1'
    )


@patch('mash.utils.azure.get_blob_url')
@patch('mash.utils.azure.get_blob_service_with_account_keys')
@patch('mash.utils.azure.get_classic_blob_service')
def test_copy_blob_to_classic_storage_failed(
    mock_get_classic_blob_service, mock_get_blob_service,
    mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'

    copy = MagicMock()
    copy.status = 'failed'

    blob_service = MagicMock()
    blob_service.copy_blob.return_value = copy
    mock_get_classic_blob_service.return_value = blob_service

    with raises(MashAzureUtilsException) as error:
        copy_blob_to_classic_storage(
            'test/data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
            'dc2', 'drg2', 'dsa2', is_page_blob=True
        )

    assert str(error.value) == 'Azure blob copy failed.'


@patch('mash.utils.azure.get_blob_service_with_account_keys')
def test_delete_blob(mock_get_blob_service):
    blob_service = MagicMock()
    mock_get_blob_service.return_value = blob_service

    delete_blob(
        'test/data/azure_creds.json', 'blob1', 'container1', 'rg1', 'sa1'
    )

    blob_service.delete_blob.assert_called_once_with(
        'container1',
        'blob1'
    )


@patch('mash.utils.azure.get_client_from_auth_file')
def test_delete_image(mock_get_client):
    compute_client = MagicMock()
    async_wait = MagicMock()
    compute_client.images.delete.return_value = async_wait
    mock_get_client.return_value = compute_client

    delete_image(
        'test/data/azure_creds.json', 'rg1', 'image123'
    )
    compute_client.images.delete.assert_called_once_with(
        'rg1', 'image123'
    )
    async_wait.wait.assert_called_once_with()


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_go_live_with_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    response = go_live_with_cloud_partner_offer(
        credentials, 'sles', 'suse'
    )

    assert response == '/api/endpoint/url'


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_publish_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    response = publish_cloud_partner_offer(
        credentials, 'sles', 'suse'
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
    callback.info.assert_called_once_with(
        'Publishing the image 30% complete.'
    )


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_put_cloud_partner_offer_doc(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'response': 'doc'}
    mock_requests.put.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    request_doc = {'test': 'doc'}

    response = put_cloud_partner_offer_doc(
        credentials, request_doc, 'sles', 'suse'
    )

    assert response['response'] == 'doc'


@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_request_cloud_partner_offer_doc(
    mock_requests, mock_acquire_access_token
):
    mock_acquire_access_token.return_value = '1234567890'
    response = MagicMock()
    response.json.return_value = {'offer': 'doc'}
    mock_requests.get.return_value = response

    with open('test/data/azure_creds.json') as f:
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
                {
                    'planId': 'gen1',
                    'diskGenerations': [{'planId': 'image-gen2'}]
                }
            ]
        }
    }

    doc = update_cloud_partner_offer_doc(
        doc,
        'blob/url/.vhd',
        'New image for v123',
        'new-image',
        'New Image 123',
        'gen1',
        generation_id='image-gen2',
        cloud_image_name_generation_suffix='gen2'
    )

    plan = doc['definition']['plans'][0]
    assert plan[vm_images_key][release]['label'] == 'New Image 123'
    assert plan['diskGenerations'][0][vm_images_key][release]['mediaName'] == \
        'new-image-gen2'


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


@patch('mash.utils.azure.log_operation_response_status')
@patch('mash.utils.azure.time')
@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
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

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    wait_on_cloud_partner_operation(
        credentials, '/api/test/operation', callback
    )


@patch('mash.utils.azure.time')
@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_wait_on_cloud_partner_operation_failed(
    mock_requests, mock_acquire_access_token, mock_time
):
    mock_acquire_access_token.return_value = '1234567890'
    callback = MagicMock()
    response = MagicMock()
    response.json.return_value = {'status': 'failed'}
    mock_requests.get.return_value = response

    with open('test/data/azure_creds.json') as f:
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
@patch('mash.utils.azure.create_json_file')
@patch('mash.utils.azure.get_client_from_auth_file')
@patch('mash.utils.azure.PageBlobService')
@patch('mash.utils.azure.FileType')
@patch('mash.utils.azure.lzma')
def test_upload_azure_file(
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

    upload_azure_file(
        'name.vhd',
        'container',
        'file.vhdfixed.xz',
        5,
        8,
        'storage',
        credentials=credentials,
        resource_group='group_name',
        is_page_blob=True
    )

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

    # Test sas token upload
    mock_PageBlobService.reset_mock()
    upload_azure_file(
        'name.vhd',
        'container',
        'file.vhdfixed.xz',
        5,
        8,
        'storage',
        sas_token='sas_token',
        is_page_blob=True
    )
    mock_PageBlobService.assert_called_once_with(
        account_name='storage',
        sas_token='sas_token'
    )

    # Test image blob create exception
    system_image_file_type.is_xz.return_value = False
    page_blob_service.create_blob_from_stream.side_effect = Exception

    # Assert raises exception if create blob fails
    with raises(MashAzureUtilsException):
        upload_azure_file(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            5,
            8,
            'storage',
            credentials=credentials,
            resource_group='group_name',
            is_page_blob=True
        )

    # Assert raises exception if missing required args
    with raises(MashAzureUtilsException):
        upload_azure_file(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            5,
            8,
            'storage',
            is_page_blob=True
        )


@patch('mash.utils.azure.BlockBlobService')
def test_get_blob_service_with_sas_token(mock_block_blob_service):
    blob_service = MagicMock()
    mock_block_blob_service.return_value = blob_service
    service = get_blob_service_with_sas_token('storage', 'sas_token')
    assert service == blob_service
