import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_azure(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
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

    response = Mock()
    response.json.return_value = request
    mock_handle_request.return_value = response

    result = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 201
    assert result.json['account_name'] == 'test'
    assert result.json['region'] == 'useast'

    # Exception
    mock_handle_request.side_effect = Exception('Failed to add Azure account')

    result = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Failed to add Azure account"}\n'


@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_azure(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    mock_jwt_identity.return_value = 'user1'

    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response

    result = test_client.delete('/accounts/azure/test')

    assert result.status_code == 200
    assert result.data == b'{"msg":"Azure account deleted"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}

    result = test_client.delete('/accounts/azure/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"Azure account not found"}\n'

    # Exception
    mock_handle_request.side_effect = Exception('Broken')

    result = test_client.delete('/accounts/azure/test')
    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete Azure account failed"}\n'


@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_azure(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'test',
        'region': 'useast',
        'source_container': 'container1',
        'source_resource_group': 'group1',
        'source_storage_account': 'account1',
        'destination_container': 'container2',
        'destination_resource_group': 'group2',
        'destination_storage_account': 'account2'
    }

    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/azure/test')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['name'] == "test"
    assert result.json['region'] == "useast"
    assert result.json['source_container'] == "container1"
    assert result.json['source_resource_group'] == "group1"
    assert result.json['source_storage_account'] == "account1"
    assert result.json['destination_container'] == "container2"
    assert result.json['destination_resource_group'] == "group2"
    assert result.json['destination_storage_account'] == "account2"

    # Not found
    response.json.return_value = {}

    result = test_client.get('/accounts/azure/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"Azure account not found"}\n'


@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_azure(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'test',
        'region': 'useast',
        'source_container': 'container1',
        'source_resource_group': 'group1',
        'source_storage_account': 'account1',
        'destination_container': 'container2',
        'destination_resource_group': 'group2',
        'destination_storage_account': 'account2'
    }

    response = Mock()
    response.json.return_value = [account]
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/azure/')

    assert result.status_code == 200
    assert result.json[0]['id'] == "1"
    assert result.json[0]['name'] == "test"
    assert result.json[0]['region'] == "useast"
    assert result.json[0]['source_container'] == "container1"
    assert result.json[0]['source_resource_group'] == "group1"
    assert result.json[0]['source_storage_account'] == "account1"
    assert result.json[0]['destination_container'] == "container2"
    assert result.json[0]['destination_resource_group'] == "group2"
    assert result.json[0]['destination_storage_account'] == "account2"


@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.routes.accounts.azure.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_azure(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'test',
        'region': 'useast',
        'source_container': 'container1',
        'source_resource_group': 'group1',
        'source_storage_account': 'account1',
        'destination_container': 'container2',
        'destination_resource_group': 'group2',
        'destination_storage_account': 'account2'
    }

    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    request = {
        'region': 'uswest'
    }

    result = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 200
    assert result.json['name'] == 'test'

    # Account not found
    response.json.return_value = {}

    result = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"Azure account not found"}\n'

    # Mash Exception
    mock_handle_request.side_effect = MashException('Broken')

    result = test_client.post(
        '/accounts/azure/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Broken"}\n'
