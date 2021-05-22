import json

from unittest.mock import patch, call, Mock


@patch('mash.services.api.v1.utils.users.handle_request')
@patch('mash.services.api.v1.routes.auth.add_token_to_database')
@patch('mash.services.api.v1.routes.auth.create_refresh_token')
@patch('mash.services.api.v1.routes.auth.create_access_token')
@patch('mash.services.api.v1.routes.auth.current_app')
def test_api_login(
        mock_current_app,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_add_token_to_database,
        mock_handle_request,
        test_client
):
    mock_current_app.config = {'AUTH_METHODS': ['password']}
    data = {'email': 'user1@fake.com', 'password': 'super-secret'}

    # Password is dirty
    mock_handle_request.side_effect = Exception(
        'Password change is required before you can login.'
    )

    response = test_client.post(
        '/v1/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 403
    assert response.data == \
        b'{"msg":"Password change is required before you can login."}\n'

    # Email or password invalid
    response = Mock()
    response.json.return_value = {}
    mock_handle_request.side_effect = None
    mock_handle_request.return_value = response

    result = test_client.post(
        '/v1/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 401
    assert result.data == b'{"msg":"Email or password is invalid"}\n'

    # Success
    response.json.return_value = {'id': '1'}
    access_token = '54321'
    refresh_token = '12345'

    mock_create_access_token.return_value = access_token
    mock_create_refresh_token.return_value = refresh_token

    result = test_client.post(
        '/v1/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_add_token_to_database.assert_has_calls([
        call(access_token, '1'),
        call(refresh_token, '1')
    ])

    assert result.status_code == 200
    assert result.json['access_token'] == '54321'
    assert result.json['refresh_token'] == '12345'

    # Password login disabled
    mock_current_app.config = {'AUTH_METHODS': ['oauth2']}

    result = test_client.post(
        '/v1/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 403
    assert result.data == b'{"msg":"Password based login is disabled"}\n'


@patch('mash.services.api.v1.routes.auth.revoke_token_by_jti')
@patch('mash.services.api.v1.routes.auth.get_jwt')
@patch('mash.services.api.v1.routes.auth.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_logout(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_jwt,
        mock_revoke_token_by_jti,
        test_client
):
    jwt = {'jti': '123'}
    mock_get_jwt.return_value = jwt
    mock_jwt_identity.return_value = 'user1'
    mock_revoke_token_by_jti.return_value = 1

    response = test_client.delete('/v1/auth/logout')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Successfully logged out"}\n'

    # Failed logout
    mock_revoke_token_by_jti.return_value = 0

    response = test_client.delete('/v1/auth/logout')

    assert response.status_code == 400
    assert response.data == b'{"msg":"Logout failed"}\n'


@patch('mash.services.api.v1.routes.auth.current_app')
def test_api_oauth2_get(
        mock_current_app,
        test_client
):
    mock_current_app.config = {
        'AUTH_METHODS': ['oauth2'],
        'OAUTH2_CLIENT_ID': 'oauth2_client_id',
        'OAUTH2_CLIENT_SECRET': 'oauth2_client_secret',
        'OAUTH2_PROVIDER_URL': 'https://oauth2.prodvider/authorize',
        'OAUTH2_REDIRECT_PORTS': [9000]
    }

    response = test_client.get('/v1/auth/oauth2')

    assert response.status_code == 200
    assert response.json['msg'] == 'Please open the following URL and log in'
    assert response.json['redirect_ports'] == [9000]

    mock_current_app.config = {'AUTH_METHODS': ['password']}

    response = test_client.get(
        '/v1/auth/oauth2',
        content_type='application/json'
    )

    assert response.status_code == 403


@patch('mash.services.api.v1.routes.auth.add_token_to_database')
@patch('mash.services.api.v1.routes.auth.create_refresh_token')
@patch('mash.services.api.v1.routes.auth.create_access_token')
@patch('mash.services.api.v1.utils.users.handle_request')
@patch('mash.services.api.v1.routes.auth.email_in_whitelist')
@patch('mash.services.api.v1.routes.auth.decode_token')
@patch('mash.services.api.v1.routes.auth.OAuth2Session')
@patch('mash.services.api.v1.routes.auth.current_app')
def test_oauth2_login(
        mock_current_app,
        mock_oauth2_session,
        mock_decode_token,
        mock_email_in_whitelist,
        mock_handle_request,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_add_token_to_database,
        test_client
):
    mock_current_app.config = {
        'AUTH_METHODS': ['oauth2'],
        'OAUTH2_CLIENT_ID': 'oauth2_client_id',
        'OAUTH2_CLIENT_SECRET': 'oauth2_client_secret',
        'OAUTH2_PROVIDER_URL': 'https://oauth2.prodvider/authorize',
        'OAUTH2_REDIRECT_PORTS': [9000]
    }
    data = {
        'auth_code': 'abcdef',
        'state': 'state-1234-5678',
        'redirect_port': 9000
    }

    mock_oauth2_session.fetch_token.return_value = {
        'access_token': 'access_token_value',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': 'openid email',
        'refresh_token': 'refresh_token_value',
        'id_token': 'id_token_value'
    }
    mock_decode_token.return_value = {'email': 'user1@fake.com'}
    mock_email_in_whitelist.return_value = False
    result = Mock()
    result.json.return_value = {'id': '1'}
    mock_handle_request.return_value = result

    response = test_client.post(
        '/v1/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 401
    assert response.data == b'{"msg":"Email is invalid"}\n'

    # Success
    mock_email_in_whitelist.return_value = True
    access_token = '54321'
    refresh_token = '12345'

    mock_create_access_token.return_value = access_token
    mock_create_refresh_token.return_value = refresh_token

    response = test_client.post(
        '/v1/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_add_token_to_database.assert_has_calls([
        call(access_token, '1'),
        call(refresh_token, '1')
    ])

    assert response.status_code == 200
    assert response.json['access_token'] == '54321'
    assert response.json['refresh_token'] == '12345'

    # Fail with token error
    mock_decode_token.side_effect = Exception('token error')
    response = test_client.post(
        '/v1/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 500

    # Fail with auth method denied
    mock_current_app.config = {'AUTH_METHODS': ['password']}

    response = test_client.post(
        '/v1/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 403
