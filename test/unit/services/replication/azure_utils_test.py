import io

from pytest import raises
from unittest.mock import MagicMock, patch

from mash.mash_exceptions import MashReplicationException
from mash.services.replication.azure_utils import (
    create_auth_file,
    delete_page_blob,
    get_classic_storage_account_keys,
    get_blob_url,
    copy_blob_to_classic_storage,
    get_page_blob_service
)
from mash.utils.json_format import JsonFormat


@patch('mash.services.replication.azure_utils.os')
@patch('mash.services.replication.azure_utils.NamedTemporaryFile')
def test_create_auth_file(mock_temp_file, mock_os):
    auth_file = MagicMock()
    auth_file.name = 'test.json'
    mock_temp_file.return_value = auth_file

    creds = {'tenantId': '123456', 'subscriptionId': '98765'}
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        with create_auth_file(creds) as auth:
            assert auth == 'test.json'

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(JsonFormat.json_message(creds))

    mock_os.remove.assert_called_once_with('test.json')


@patch('mash.services.replication.azure_utils.adal')
@patch('mash.services.replication.azure_utils.requests')
def test_get_classic_storage_account_keys(mock_requests, mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context
    response = MagicMock()
    response.json.return_value = {'primaryKey': '123', 'secondaryKey': '321'}
    mock_requests.post.return_value = response

    keys = get_classic_storage_account_keys(
        '../data/azure_creds.json', 'rg1', 'sa1'
    )

    mock_adal.AuthenticationContext.assert_called_once_with(
        'https://login.microsoftonline.com/'
        '09876543-1234-1234-1234-123456789012'
    )
    context.acquire_token_with_client_credentials.assert_called_once_with(
        'https://management.core.windows.net/',
        '09876543-1234-1234-1234-123456789012',
        '09876543-1234-1234-1234-123456789012'
    )
    assert keys['primaryKey'] == '123'
    assert keys['secondaryKey'] == '321'


@patch('mash.services.replication.azure_utils.get_page_blob_service')
def test_get_blob_url(mock_get_page_blob_service):
    page_blob_service = MagicMock()
    page_blob_service.generate_container_shared_access_signature \
        .return_value = 'token123'
    page_blob_service.make_blob_url.return_value = 'https://test/url/?token123'
    mock_get_page_blob_service.return_value = page_blob_service

    url = get_blob_url(
        '../data/azure_creds.json', 'blob1', 'container1', 'rg1', 'sa1'
    )

    assert url == 'https://test/url/?token123'
    page_blob_service.make_blob_url.assert_called_once_with(
        'container1',
        'blob1',
        sas_token='token123'
    )


@patch('mash.services.replication.azure_utils.get_client_from_auth_file')
@patch('mash.services.replication.azure_utils.PageBlobService')
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


@patch('mash.services.replication.azure_utils.get_blob_url')
@patch('mash.services.replication.azure_utils.get_classic_storage_account_keys')
@patch('mash.services.replication.azure_utils.time.sleep')
@patch('mash.services.replication.azure_utils.PageBlobService')
def test_copy_blob_to_classic_storage(
    mock_page_blob_service, mock_time, mock_get_keys, mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'
    keys = {'primaryKey': '123456'}
    mock_get_keys.return_value = keys

    copy = MagicMock()
    copy.status = 'pending'

    props_copy = MagicMock()
    props_copy.properties.copy.status = 'success'

    page_blob_service = MagicMock()
    page_blob_service.copy_blob.return_value = copy
    page_blob_service.get_blob_properties.return_value = props_copy
    mock_page_blob_service.return_value = page_blob_service

    copy_blob_to_classic_storage(
        '../data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
        'dc2', 'drg2', 'dsa2'
    )

    mock_get_blob_url.assert_called_once_with(
        '../data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1'
    )

    mock_get_keys.assert_called_once_with(
        '../data/azure_creds.json', 'drg2', 'dsa2'
    )


@patch('mash.services.replication.azure_utils.get_blob_url')
@patch('mash.services.replication.azure_utils.get_classic_storage_account_keys')
@patch('mash.services.replication.azure_utils.time.sleep')
@patch('mash.services.replication.azure_utils.PageBlobService')
def test_copy_blob_to_classic_storage_timeout(
    mock_page_blob_service, mock_time, mock_get_keys, mock_get_blob_url
):
    mock_get_blob_url.return_value = 'https://test/url/?token123'
    keys = {'primaryKey': '123456'}
    mock_get_keys.return_value = keys

    copy = MagicMock()
    copy.status = 'pending'

    props_copy = MagicMock()
    props_copy.properties.copy.status = 'success'

    page_blob_service = MagicMock()
    page_blob_service.copy_blob.return_value = copy
    page_blob_service.get_blob_properties.return_value = props_copy
    mock_page_blob_service.return_value = page_blob_service

    with raises(MashReplicationException):
        copy_blob_to_classic_storage(
            '../data/azure_creds.json', 'blob1', 'sc1', 'srg1', 'ssa1',
            'dc2', 'drg2', 'dsa2', timeout=0
        )


@patch('mash.services.replication.azure_utils.get_page_blob_service')
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
