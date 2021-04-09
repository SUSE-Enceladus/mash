import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.v1.utils.accounts.gce.handle_request')
@patch('mash.services.api.v1.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_gce(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    mock_jwt_identity.return_value = 'user1'
    request = {
        'account_name': 'test',
        'credentials': {
            'type': 'string',
            'project_id': 'string',
            'private_key_id': 'string',
            'private_key': 'string',
            'client_email': 'string',
            'client_id': 'string',
            'auth_uri': 'string',
            'token_uri': 'string',
            'auth_provider_x509_cert_url': 'string',
            'client_x509_cert_url': 'string'
        },
        'bucket': 'bucket1',
        'region': 'us-east-1'
    }
    response = Mock()
    response.json.return_value = request
    mock_handle_request.return_value = response

    result = test_client.post(
        '/v1/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 201

    # Exception
    mock_handle_request.side_effect = Exception('Failed to add GCE account')

    result = test_client.post(
        '/v1/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Failed to add GCE account"}\n'


@patch('mash.services.api.v1.utils.accounts.gce.handle_request')
@patch('mash.services.api.v1.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_gce(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/v1/accounts/gce/test')

    assert result.status_code == 200
    assert result.data == b'{"msg":"GCE account deleted"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}

    result = test_client.delete('/v1/accounts/gce/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"GCE account not found"}\n'

    # Exception
    mock_handle_request.side_effect = Exception('Broken')

    result = test_client.delete('/v1/accounts/gce/test')
    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete GCE account failed"}\n'


@patch('mash.services.api.v1.utils.accounts.gce.handle_request')
@patch('mash.services.api.v1.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_gce(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-east-1',
        'testing_account': None,
        'is_publishing_account': False
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/v1/accounts/gce/test')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['name'] == "user1"
    assert result.json['bucket'] == "images"
    assert result.json['region'] == "us-east-1"

    # Not found
    response.json.return_value = {}

    result = test_client.get('/v1/accounts/gce/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"GCE account not found"}\n'


@patch('mash.services.api.v1.utils.accounts.gce.handle_request')
@patch('mash.services.api.v1.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_gce(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-east-1',
        'testing_account': None,
        'is_publishing_account': False
    }
    response = Mock()
    response.json.return_value = [account]
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/v1/accounts/gce/')

    assert result.status_code == 200
    assert result.json[0]['id'] == "1"
    assert result.json[0]['name'] == "user1"
    assert result.json[0]['bucket'] == "images"
    assert result.json[0]['region'] == "us-east-1"


@patch('mash.services.api.v1.utils.accounts.gce.handle_request')
@patch('mash.services.api.v1.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_gce(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-east-1',
        'testing_account': None,
        'is_publishing_account': False
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    request = {
        'bucket': 'bucket1',
        'region': 'us-east-1'
    }

    result = test_client.post(
        '/v1/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 200

    # Account not found
    response.json.return_value = {}

    result = test_client.post(
        '/v1/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"GCE account not found"}\n'

    # Mash Exception
    mock_handle_request.side_effect = MashException('Broken')

    result = test_client.post(
        '/v1/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Broken"}\n'
