import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound


@patch('mash.services.database.utils.accounts.azure.handle_request')
@patch('mash.services.database.utils.accounts.azure.db')
def test_add_account_azure(
    mock_db,
    mock_handle_request,
    test_client
):
    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'region': 'useast',
        "source_container": "string",
        "source_resource_group": "string",
        "source_storage_account": "string",
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
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['name'] == 'test'
    assert response.json['region'] == 'useast'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create azure account: Broken"}\n'

    # Integrity Error
    mock_db.session.commit.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Account already exists"}\n'


@patch('mash.services.database.utils.accounts.azure.get_azure_account_by_user')
@patch('mash.services.database.utils.accounts.azure.handle_request')
@patch('mash.services.database.utils.accounts.azure.db')
def test_delete_account_azure(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'

    mock_get_account.return_value = account
    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.delete(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete Azure account failed"}\n'

    # Not found
    mock_get_account.return_value = None

    response = test_client.delete(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.accounts.azure.handle_request')
@patch('mash.services.database.utils.accounts.azure.AzureAccount')
def test_get_account_azure(
    mock_azure_account,
    mock_handle_request,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'

    queryset = Mock()
    queryset.one.return_value = account
    mock_azure_account.query.filter_by.return_value = queryset

    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "test"
    assert response.json['region'] == "useast"
    assert response.json['source_container'] == "container1"
    assert response.json['source_resource_group'] == "group1"
    assert response.json['source_storage_account'] == "account1"

    # Not found
    mock_azure_account.query.filter_by.side_effect = NoResultFound()

    response = test_client.get(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'


@patch('mash.services.database.utils.accounts.azure.get_user_by_id')
def test_get_account_list_azure(mock_get_user, test_client):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'

    user = Mock()
    user.azure_accounts = [account]
    mock_get_user.return_value = user

    response = test_client.get('/azure_accounts/list/user1')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "test"
    assert response.json[0]['region'] == "useast"
    assert response.json[0]['source_container'] == "container1"
    assert response.json[0]['source_resource_group'] == "group1"
    assert response.json[0]['source_storage_account'] == "account1"


@patch('mash.services.database.utils.accounts.azure.get_azure_account_by_user')
@patch('mash.services.database.utils.accounts.azure.handle_request')
@patch('mash.services.database.utils.accounts.azure.db')
def test_update_account_azure(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'test'
    account.region = 'useast'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'

    mock_get_account.return_value = account

    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'region': 'useast',
        "source_container": "string",
        "source_resource_group": "string",
        "source_storage_account": "string",
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

    response = test_client.put(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200

    # DB Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update Azure account failed"}\n'

    # Request exception
    mock_handle_request.side_effect = Exception('Broken')

    response = test_client.put(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update Azure account failed"}\n'

    # Account not found
    mock_get_account.return_value = None

    response = test_client.put(
        '/azure_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'
