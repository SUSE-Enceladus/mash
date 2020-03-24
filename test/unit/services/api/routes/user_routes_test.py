import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashDBException


@patch('mash.services.api.routes.user.current_app')
@patch('mash.services.api.routes.user.add_user')
def test_api_create_user(mock_add_user, mock_current_app, test_client):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'

    mock_add_user.return_value = user
    mock_current_app.config = {'AUTH_METHODS': ['password']}

    data = {
        'email': 'user1@fake.com',
        'password': 'secretpassword123'
    }
    response = test_client.post(
        '/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_add_user.assert_called_once_with(
        'user1@fake.com',
        'secretpassword123'
    )

    assert response.status_code == 201
    assert response.json['id'] == "1"
    assert response.json['email'] == "user1@fake.com"

    # User exists
    mock_add_user.return_value = None

    response = test_client.post(
        '/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 409
    assert response.data == b'{"msg":"Email already in use"}\n'

    # Password too short
    data['password'] = 'secret'
    mock_add_user.side_effect = MashDBException(
        'Password too short. Minimum length is 8 characters.'
    )
    response = test_client.post(
        '/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == \
        b'{"errors":{"password":"Password too short. ' \
        b'Minimum length is 8 characters."},"message":' \
        b'"Input payload validation failed"}\n'

    # Fail with forbidden auth method
    mock_current_app.config = {'AUTH_METHODS': ['oauth2']}

    response = test_client.post(
        '/user/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 403


@patch('mash.services.api.routes.user.get_user_by_id')
@patch('mash.services.api.routes.user.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_user(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_user,
        test_client
):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user
    mock_jwt_identity.return_value = '1'

    response = test_client.get('/user/')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['email'] == "user1@fake.com"


@patch('mash.services.api.routes.user.delete_user')
@patch('mash.services.api.routes.user.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_user(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_user,
        test_client
):
    mock_delete_user.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete('/user/')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Account deleted"}\n'

    # Not found
    mock_delete_user.return_value = 0
    response = test_client.delete('/user/')

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete account failed"}\n'


@patch('mash.services.api.routes.user.reset_user_password')
def test_api_password_reset(
    mock_reset_password,
    test_client
):
    mock_reset_password.return_value = 1

    data = {'email': 'user1@fake.com'}

    response = test_client.post(
        '/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert b'Password reset submitted.' in response.data

    # Not found
    mock_reset_password.return_value = 0
    response = test_client.post(
        '/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 404
    assert response.data == b'{"msg":"Password reset failed."}\n'


@patch('mash.services.api.routes.user.change_user_password')
def test_api_password_change(
    mock_change_password,
    test_client
):
    mock_change_password.return_value = 1

    data = {
        'email': 'user1@fake.com',
        'current_password': 'pass',
        'new_password': 'betterpassword'
    }

    response = test_client.put(
        '/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert b'Password changed successfully.' in response.data

    # Not found
    mock_change_password.return_value = 0
    response = test_client.put(
        '/user/password',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 404
    assert response.data == b'{"msg":"Password change failed."}\n'
