import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_ec2(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
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
    response = Mock()
    response.json.return_value = request
    mock_handle_request.return_value = response

    result = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 201

    # Exception
    mock_handle_request.side_effect = Exception('Failed to add EC2 account')

    result = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Failed to add EC2 account"}\n'


@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_ec2(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    mock_jwt_identity.return_value = 'user1'
    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response

    result = test_client.delete('/accounts/ec2/test')

    assert result.status_code == 200
    assert result.data == b'{"msg":"EC2 account deleted"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}

    result = test_client.delete('/accounts/ec2/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"EC2 account not found"}\n'

    # Exception
    mock_handle_request.side_effect = Exception('Broken')

    result = test_client.delete('/accounts/ec2/test')
    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete EC2 account failed"}\n'


@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_ec2(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'partition': 'aws',
        'region': 'us-east-1',
        'subnet': None,
        'additional_regions': None,
        'group': None
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/ec2/test')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['name'] == "user1"
    assert result.json['partition'] == "aws"
    assert result.json['region'] == "us-east-1"

    # Not found
    response.json.return_value = {}

    result = test_client.get('/accounts/ec2/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"EC2 account not found"}\n'

    # Exception
    response.side_effect = Exception('Broken')

    result = test_client.get('/accounts/ec2/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"EC2 account not found"}\n'


@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_ec2(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'partition': 'aws',
        'region': 'us-east-1',
        'subnet': None,
        'additional_regions': None,
        'group': None
    }
    response = Mock()
    response.json.return_value = [account]
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/ec2/')

    assert result.status_code == 200
    assert result.json[0]['id'] == "1"
    assert result.json[0]['name'] == "user1"
    assert result.json[0]['partition'] == "aws"
    assert result.json[0]['region'] == "us-east-1"


@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.routes.accounts.ec2.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_ec2(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'partition': 'aws',
        'region': 'us-east-1',
        'subnet': None,
        'additional_regions': None,
        'group': None
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    request = {
        'group': 'group1',
        'region': 'us-east-1'
    }

    result = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 200

    # Account not found
    response.json.return_value = {}

    result = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"EC2 account not found"}\n'

    # Mash Exception
    mock_handle_request.side_effect = MashException('Broken')

    result = test_client.post(
        '/accounts/ec2/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Broken"}\n'
