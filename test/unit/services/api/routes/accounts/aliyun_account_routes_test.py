import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.utils.accounts.aliyun.handle_request')
@patch('mash.services.api.routes.accounts.aliyun.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_aliyun(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    mock_jwt_identity.return_value = 'user1'
    request = {
        'account_name': 'test',
        'credentials': {
            'access_key': 'string',
            'access_secret': 'string'
        },
        'bucket': 'bucket1',
        'region': 'cn-beijing'
    }
    response = Mock()
    response.json.return_value = request
    mock_handle_request.return_value = response

    result = test_client.post(
        '/accounts/aliyun/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 201

    # Exception
    mock_handle_request.side_effect = Exception('Failed to add Aliyun account')

    result = test_client.post(
        '/accounts/aliyun/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Failed to add Aliyun account"}\n'


@patch('mash.services.api.utils.accounts.aliyun.handle_request')
@patch('mash.services.api.routes.accounts.aliyun.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_aliyun(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/accounts/aliyun/test')

    assert result.status_code == 200
    assert result.data == b'{"msg":"Aliyun account deleted"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}

    result = test_client.delete('/accounts/aliyun/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"Aliyun account not found"}\n'

    # Exception
    mock_handle_request.side_effect = Exception('Broken')

    result = test_client.delete('/accounts/aliyun/test')
    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete Aliyun account failed"}\n'


@patch('mash.services.api.utils.accounts.aliyun.handle_request')
@patch('mash.services.api.routes.accounts.aliyun.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_aliyun(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'cn-beijing',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1'
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/aliyun/test')

    assert result.status_code == 200
    assert result.json['id'] == '1'
    assert result.json['name'] == 'user1'
    assert result.json['bucket'] == 'images'
    assert result.json['region'] == 'cn-beijing'
    assert result.json['security_group_id'] == 'sg1'
    assert result.json['vswitch_id'] == 'vs1'

    # Not found
    response.json.return_value = {}

    result = test_client.get('/accounts/aliyun/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"Aliyun account not found"}\n'


@patch('mash.services.api.utils.accounts.aliyun.handle_request')
@patch('mash.services.api.routes.accounts.aliyun.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_aliyun(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'cn-beijing',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1'
    }
    response = Mock()
    response.json.return_value = [account]
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/aliyun/')

    assert result.status_code == 200
    assert result.json[0]['id'] == '1'
    assert result.json[0]['name'] == 'user1'
    assert result.json[0]['bucket'] == 'images'
    assert result.json[0]['region'] == 'cn-beijing'
    assert result.json[0]['security_group_id'] == 'sg1'
    assert result.json[0]['vswitch_id'] == 'vs1'


@patch('mash.services.api.utils.accounts.aliyun.handle_request')
@patch('mash.services.api.routes.accounts.aliyun.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_aliyun(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'cn-beijing',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1'
    }
    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    request = {
        'bucket': 'bucket1',
        'region': 'cn-beijing'
    }

    result = test_client.post(
        '/accounts/aliyun/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 200

    # Account not found
    response.json.return_value = {}

    result = test_client.post(
        '/accounts/aliyun/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"Aliyun account not found"}\n'

    # Mash Exception
    mock_handle_request.side_effect = MashException('Broken')

    result = test_client.post(
        '/accounts/aliyun/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Broken"}\n'
