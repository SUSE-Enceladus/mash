import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.routes.accounts.ec2.create_ec2_account')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_ec2(
        mock_jwt_required,
        mock_jwt_identity,
        mock_create_ec2_account,
        test_client
):
    mock_jwt_identity.return_value = 'user1'
    request = {
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'group': 'group1',
        'partition': 'aws',
        'region': 'us-east-1'
    }
    response = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_create_ec2_account.assert_called_once_with(
        'user1',
        'test',
        'aws',
        'us-east-1',
        {'access_key_id': '123456', 'secret_access_key': '654321'},
        None,
        'group1',
        None
    )

    assert response.status_code == 201

    # Mash Exception
    mock_create_ec2_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Integrity Error
    mock_create_ec2_account.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 409
    assert response.data == b'{"msg":"Account already exists"}\n'

    # Exception
    mock_create_ec2_account.side_effect = Exception('Broken')

    response = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to add EC2 account"}\n'


@patch('mash.services.api.routes.accounts.ec2.delete_ec2_account')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_ec2(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_ec2_account,
        test_client
):
    mock_delete_ec2_account.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete('/accounts/ec2/test')

    assert response.status_code == 200
    assert response.data == b'{"msg":"EC2 account deleted"}\n'

    # Not found
    mock_delete_ec2_account.return_value = 0

    response = test_client.delete('/accounts/ec2/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"EC2 account not found"}\n'

    # Exception
    mock_delete_ec2_account.side_effect = Exception('Broken')

    response = test_client.delete('/accounts/ec2/test')
    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete EC2 account failed"}\n'


@patch('mash.services.api.routes.accounts.ec2.get_ec2_account')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_ec2(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_ec2_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    mock_get_ec2_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/ec2/test')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['partition'] == "aws"
    assert response.json['region'] == "us-east-1"

    # Not found
    mock_get_ec2_account.return_value = None

    response = test_client.get('/accounts/ec2/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"EC2 account not found"}\n'


@patch('mash.services.api.routes.accounts.ec2.get_ec2_accounts')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_ec2(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_ec2_accounts,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    mock_get_ec2_accounts.return_value = [account]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/ec2/')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['partition'] == "aws"
    assert response.json[0]['region'] == "us-east-1"


@patch('mash.services.api.routes.accounts.ec2.update_ec2_account')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_ec2(
        mock_jwt_required,
        mock_jwt_identity,
        mock_update_ec2_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    mock_update_ec2_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    request = {
        'group': 'group1',
        'region': 'us-east-1'
    }

    response = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_update_ec2_account.assert_called_once_with(
        'acnt1',
        'user1',
        None,
        None,
        'group1',
        'us-east-1',
        None
    )

    assert response.status_code == 200

    # Mash Exception
    mock_update_ec2_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Account not found
    mock_update_ec2_account.side_effect = None
    mock_update_ec2_account.return_value = None

    response = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"EC2 account not found"}\n'
