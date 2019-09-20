import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.routes.accounts.azure.create_azure_account')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_azure(
        mock_jwt_required,
        mock_jwt_identity,
        mock_create_azure_account,
        test_client
):
    mock_jwt_identity.return_value = 'user1'
    request = {
        'account_name': 'test',
        'region': 'useast',
        "source_container": "string",
        "source_resource_group": "string",
        "source_storage_account": "string",
        "destination_container": "string",
        "destination_resource_group": "string",
        "destination_storage_account": "string",
        "credentials": {
            "clientId": "string",
            "clientSecret": "string",
            "subscriptionId": "string",
            "tenantId": "string",
            "activeDirectoryEndpointUrl": "string",
            "resourceManagerEndpointUrl": "string",
            "activeDirectoryGraphResourceId": "string",
            "sqlManagementEndpointUrl": "string",
            "galleryEndpointUrl": "string",
            "managementEndpointUrl": "string"
        }
    }
    response = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_create_azure_account.assert_called_once_with(
        'user1',
        'test',
        'useast',
        {
            "clientId": "string",
            "clientSecret": "string",
            "subscriptionId": "string",
            "tenantId": "string",
            "activeDirectoryEndpointUrl": "string",
            "resourceManagerEndpointUrl": "string",
            "activeDirectoryGraphResourceId": "string",
            "sqlManagementEndpointUrl": "string",
            "galleryEndpointUrl": "string",
            "managementEndpointUrl": "string"
        },
        "string",
        "string",
        "string",
        "string",
        "string",
        "string"
    )

    assert response.status_code == 201

    # Mash Exception
    mock_create_azure_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Integrity Error
    mock_create_azure_account.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 409
    assert response.data == b'{"msg":"Account already exists"}\n'

    # Exception
    mock_create_azure_account.side_effect = Exception('Broken')

    response = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to add Azure account"}\n'


@patch('mash.services.api.routes.accounts.azure.delete_azure_account')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_azure(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_azure_account,
        test_client
):
    mock_delete_azure_account.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete('/accounts/azure/test')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Azure account deleted"}\n'

    # Not found
    mock_delete_azure_account.return_value = 0

    response = test_client.delete('/accounts/azure/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"Azure account not found"}\n'

    # Exception
    mock_delete_azure_account.side_effect = Exception('Broken')

    response = test_client.delete('/accounts/azure/test')
    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete Azure account failed"}\n'


@patch('mash.services.api.routes.accounts.azure.get_azure_account')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_azure(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_azure_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'
    account.destination_container = 'container2'
    account.destination_resource_group = 'group2'
    account.destination_storage_account = 'account2'

    mock_get_azure_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/azure/test')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "test"
    assert response.json['region'] == "useast"
    assert response.json['source_container'] == "container1"
    assert response.json['source_resource_group'] == "group1"
    assert response.json['source_storage_account'] == "account1"
    assert response.json['destination_container'] == "container2"
    assert response.json['destination_resource_group'] == "group2"
    assert response.json['destination_storage_account'] == "account2"

    # Not found
    mock_get_azure_account.return_value = None

    response = test_client.get('/accounts/azure/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"Azure account not found"}\n'


@patch('mash.services.api.routes.accounts.azure.get_azure_accounts')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_azure(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_azure_accounts,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'
    account.destination_container = 'container2'
    account.destination_resource_group = 'group2'
    account.destination_storage_account = 'account2'

    mock_get_azure_accounts.return_value = [account]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/azure/')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "test"
    assert response.json[0]['region'] == "useast"
    assert response.json[0]['source_container'] == "container1"
    assert response.json[0]['source_resource_group'] == "group1"
    assert response.json[0]['source_storage_account'] == "account1"
    assert response.json[0]['destination_container'] == "container2"
    assert response.json[0]['destination_resource_group'] == "group2"
    assert response.json[0]['destination_storage_account'] == "account2"


@patch('mash.services.api.routes.accounts.azure.update_azure_account')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_update_azure_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'
    account.destination_container = 'container2'
    account.destination_resource_group = 'group2'
    account.destination_storage_account = 'account2'

    mock_update_azure_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    request = {
        'region': 'uswest'
    }

    response = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_update_azure_account.assert_called_once_with(
        'acnt1',
        'user1',
        'uswest',
        None,
        None,
        None,
        None,
        None,
        None,
        None
    )

    assert response.status_code == 200

    # Mash Exception
    mock_update_azure_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Account not found
    mock_update_azure_account.side_effect = None
    mock_update_azure_account.return_value = None

    response = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"Azure account not found"}\n'
