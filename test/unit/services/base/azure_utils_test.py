from unittest.mock import MagicMock, patch

from mash.utils.azure import (
    get_blob_url,
    get_blob_service_with_account_keys,
    get_blob_service_with_sas_token,
    get_client_from_json
)

creds = {
    "clientId": "09876543-1234-1234-1234-123456789012",
    "clientSecret": "09876543-1234-1234-1234-123456789012",
    "subscriptionId": "09876543-1234-1234-1234-123456789012",
    "tenantId": "09876543-1234-1234-1234-123456789012"
}


@patch('mash.utils.azure.generate_container_sas')
def test_get_blob_url(mock_generate_container_sas):
    blob_service = MagicMock()
    blob_service.credential.account_key = 'key123'
    mock_generate_container_sas.return_value = 'token123'

    url = get_blob_url(
        blob_service, 'blob1', 'sa1', 'container1'
    )

    sas_url = 'https://sa1.blob.core.windows.net/container1/blob1?token123'
    assert url == sas_url


@patch('mash.utils.azure.get_client_from_json')
@patch('mash.utils.azure.BlobServiceClient')
def test_get_blob_service_with_account_keys(
    mock_blob_service,
    mock_get_client_from_json
):
    storage_client = MagicMock()
    mock_get_client_from_json.return_value = storage_client

    key1 = MagicMock()
    key1.value = '12345678'
    key2 = MagicMock()
    key2.value = '87654321'
    key_list = MagicMock()
    key_list.keys = [key1, key2]
    storage_client.storage_accounts.list_keys.return_value = key_list

    blob_service = MagicMock()
    mock_blob_service.return_value = blob_service

    service = get_blob_service_with_account_keys(
        creds, 'rg1', 'sa1'
    )

    assert service == blob_service
    storage_client.storage_accounts.list_keys.assert_called_once_with(
        'rg1', 'sa1'
    )
    mock_blob_service.assert_called_once_with(
        account_url='https://sa1.blob.core.windows.net',
        credential='12345678'
    )


@patch('mash.utils.azure.BlobServiceClient')
def test_get_blob_service_with_sas_token(mock_blob_service):
    blob_service = MagicMock()
    mock_blob_service.return_value = blob_service
    service = get_blob_service_with_sas_token('storage', 'sas_token')
    assert service == blob_service


@patch('mash.utils.azure.ClientSecretCredential')
def test_get_client_from_json(mock_cred_client):
    cred = MagicMock()
    client = MagicMock()
    mock_cred_client.return_value = cred

    get_client_from_json(client, creds)

    mock_cred_client.assert_called_once_with(
        tenant_id=creds['tenantId'],
        client_id=creds['clientId'],
        client_secret=creds['clientSecret']
    )
