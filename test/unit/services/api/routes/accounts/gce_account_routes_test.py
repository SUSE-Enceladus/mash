import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.routes.accounts.gce.create_gce_account')
@patch('mash.services.api.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_create_gce_account,
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
    response = test_client.post(
        '/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_create_gce_account.assert_called_once_with(
        'user1',
        'test',
        'bucket1',
        'us-east-1',
        {
            'auth_provider_x509_cert_url': 'string',
            'auth_uri': 'string',
            'client_email': 'string',
            'client_id': 'string',
            'client_x509_cert_url': 'string',
            'private_key': 'string',
            'private_key_id': 'string',
            'project_id': 'string',
            'token_uri': 'string',
            'type': 'string'
        },
        None,
        False
    )

    assert response.status_code == 201

    # Mash Exception
    mock_create_gce_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Integrity Error
    mock_create_gce_account.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 409
    assert response.data == b'{"msg":"Account already exists"}\n'

    # Exception
    mock_create_gce_account.side_effect = Exception('Broken')

    response = test_client.post(
        '/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to add GCE account"}\n'


@patch('mash.services.api.routes.accounts.gce.delete_gce_account')
@patch('mash.services.api.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_gce_account,
        test_client
):
    mock_delete_gce_account.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete('/accounts/gce/test')

    assert response.status_code == 200
    assert response.data == b'{"msg":"GCE account deleted"}\n'

    # Not found
    mock_delete_gce_account.return_value = 0

    response = test_client.delete('/accounts/gce/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"GCE account not found"}\n'

    # Exception
    mock_delete_gce_account.side_effect = Exception('Broken')

    response = test_client.delete('/accounts/gce/test')
    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete GCE account failed"}\n'


@patch('mash.services.api.routes.accounts.gce.get_gce_account')
@patch('mash.services.api.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_gce_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.test_account = None
    account.is_publishing_account = False

    mock_get_gce_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/gce/test')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['bucket'] == "images"
    assert response.json['region'] == "us-east-1"

    # Not found
    mock_get_gce_account.return_value = None

    response = test_client.get('/accounts/gce/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"GCE account not found"}\n'


@patch('mash.services.api.routes.accounts.gce.get_gce_accounts')
@patch('mash.services.api.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_gce_accounts,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.test_account = None
    account.is_publishing_account = False

    mock_get_gce_accounts.return_value = [account]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/gce/')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['bucket'] == "images"
    assert response.json[0]['region'] == "us-east-1"


@patch('mash.services.api.routes.accounts.gce.update_gce_account')
@patch('mash.services.api.routes.accounts.gce.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_gce(
        mock_jwt_required,
        mock_jwt_identity,
        mock_update_gce_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.test_account = None
    account.is_publishing_account = False

    mock_update_gce_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    request = {
        'bucket': 'bucket1',
        'region': 'us-east-1'
    }

    response = test_client.post(
        '/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_update_gce_account.assert_called_once_with(
        'acnt1',
        'user1',
        'bucket1',
        'us-east-1',
        None,
        None
    )

    assert response.status_code == 200

    # Mash Exception
    mock_update_gce_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Account not found
    mock_update_gce_account.side_effect = None
    mock_update_gce_account.return_value = None

    response = test_client.post(
        '/accounts/gce/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"GCE account not found"}\n'
