import json

from unittest.mock import patch, Mock


@patch('mash.services.api.v1.routes.user.current_app')
@patch('mash.services.api.v1.utils.users.handle_request')
def test_api_create_user(mock_handle_request, mock_current_app, test_client):
    user = {
        'id': '1',
        'email': 'user1@fake.com'
    }
    response = Mock()
    response.json.return_value = user
    mock_handle_request.return_value = response
    mock_current_app.config = {'AUTH_METHODS': ['password']}

    data = {
        'email': 'user1@fake.com',
        'password': 'secretpassword123'
    }
    result = test_client.post(
        '/v1/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 201
    assert result.json['id'] == "1"
    assert result.json['email'] == "user1@fake.com"

    # User exists
    response.json.return_value = {}

    result = test_client.post(
        '/v1/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 409
    assert result.data == b'{"msg":"Email already in use"}\n'

    # Password too short
    data['password'] = 'secret'
    result = test_client.post(
        '/v1/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 400
    assert result.data == \
        b'{"msg":"Password too short. ' \
        b'Minimum length is 8 characters."}\n'

    # Fail with forbidden auth method
    mock_current_app.config = {'AUTH_METHODS': ['oauth2']}

    result = test_client.post(
        '/v1/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert result.status_code == 403


@patch('mash.services.api.v1.utils.users.handle_request')
@patch('mash.services.api.v1.routes.user.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_user(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    user = {
        'id': '1',
        'email': 'user1@fake.com'
    }
    response = Mock()
    response.json.return_value = user
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = '1'

    result = test_client.get('/v1/user/')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['email'] == "user1@fake.com"


@patch('mash.services.api.v1.utils.users.handle_request')
@patch('mash.services.api.v1.routes.user.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_user(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/v1/user/')

    assert result.status_code == 200
    assert result.data == b'{"msg":"Account deleted"}\n'

    # Not found
    mock_handle_request.side_effect = Exception('Fail')
    result = test_client.delete('/v1/user/')

    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete account failed"}\n'


@patch('mash.services.api.v1.routes.user.current_app')
@patch('mash.services.api.v1.utils.users.handle_request')
def test_api_password_reset(
    mock_handle_request,
    mock_current_app,
    test_client
):
    response = Mock()
    response.json.return_value = {'password': 'fake'}
    mock_handle_request.return_value = response

    data = {'email': 'user1@fake.com'}

    result = test_client.post(
        '/v1/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 200
    assert b'Password reset submitted.' in result.data
    mock_current_app.notification_class.send_notification.call_count == 1

    # Not found
    mock_handle_request.side_effect = Exception('Fail')
    result = test_client.post(
        '/v1/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 404
    assert result.data == b'{"msg":"Password reset failed."}\n'


@patch('mash.services.api.v1.routes.user.current_app')
@patch('mash.services.api.v1.utils.users.handle_request')
def test_api_password_change(
    mock_handle_request,
    mock_current_app,
    test_client
):
    data = {
        'email': 'user1@fake.com',
        'current_password': 'pass',
        'new_password': 'betterpassword'
    }

    result = test_client.put(
        '/v1/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 200
    assert b'Password changed successfully.' in result.data
    mock_current_app.notification_class.send_notification.call_count == 1

    # Not found
    mock_handle_request.side_effect = Exception('Password change failed.')
    result = test_client.put(
        '/v1/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 404
    assert result.data == b'{"msg":"Password change failed."}\n'

    # Password too short
    data['new_password'] = 'pass12'
    result = test_client.put(
        '/v1/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 404
    assert result.data == \
        b'{"msg":"Password too short. Minimum length is 8 characters."}\n'
