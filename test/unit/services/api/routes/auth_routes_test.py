import json

from unittest.mock import patch, call, Mock


@patch('mash.services.api.routes.auth.add_token_to_database')
@patch('mash.services.api.routes.auth.create_refresh_token')
@patch('mash.services.api.routes.auth.create_access_token')
@patch('mash.services.api.routes.auth.verify_login')
@patch('mash.services.api.routes.auth.current_app')
def test_api_login(
        mock_current_app,
        mock_verify_login,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_add_token_to_database,
        test_client
):
    mock_current_app.config = {'AUTH_METHOD': 'password'}
    mock_verify_login.return_value = False
    data = {'username': 'user1', 'password': 'super-secret'}

    response = test_client.post(
        '/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 401
    assert response.data == b'{"msg":"Username or password is invalid"}\n'

    # Success
    mock_verify_login.return_value = True
    access_token = '54321'
    refresh_token = '12345'

    mock_create_access_token.return_value = access_token
    mock_create_refresh_token.return_value = refresh_token

    response = test_client.post(
        '/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_add_token_to_database.assert_has_calls([
        call(access_token, 'user1'),
        call(refresh_token, 'user1')
    ])

    assert response.status_code == 200
    assert response.json['access_token'] == '54321'
    assert response.json['refresh_token'] == '12345'

    mock_current_app.config = {'AUTH_METHOD': 'oauth2'}

    response = test_client.post(
        '/auth/login',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 403


@patch('mash.services.api.routes.auth.revoke_token_by_jti')
@patch('mash.services.api.routes.auth.get_raw_jwt')
@patch('mash.services.api.routes.auth.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_refresh_token_in_request')
def test_api_logout(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_raw_jwt,
        mock_revoke_token_by_jti,
        test_client
):
    jwt = {'jti': '123'}
    mock_get_raw_jwt.return_value = jwt
    mock_jwt_identity.return_value = 'user1'
    mock_revoke_token_by_jti.return_value = 1

    response = test_client.delete('/auth/logout')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Successfully logged out"}\n'

    # Failed logout
    mock_revoke_token_by_jti.return_value = 0

    response = test_client.delete('/auth/logout')

    assert response.status_code == 400
    assert response.data == b'{"msg":"Logout failed"}\n'


@patch('mash.services.api.routes.auth.current_app')
def test_api_oauth2_get(
        mock_current_app,
        test_client
):
    mock_current_app.config = {
        'AUTH_METHOD': 'oauth2',
        'OAUTH2_CLIENT_ID': 'oauth2_client_id',
        'OAUTH2_CLIENT_SECRET': 'oauth2_client_secret',
        'OAUTH2_PROVIDER_URL': 'https://oauth2.prodvider/authorize',
        'OAUTH2_REDIRECT_PORTS': [9000]
    }

    response = test_client.get('/auth/oauth2')

    assert response.status_code == 200
    assert response.json['msg'] == 'Please open the following URL and log in'
    assert response.json['redirect_ports'] == [9000]

    mock_current_app.config = {'AUTH_METHOD': 'password'}

    response = test_client.get(
        '/auth/oauth2',
        content_type='application/json'
    )

    assert response.status_code == 403


@patch('mash.services.api.routes.auth.add_token_to_database')
@patch('mash.services.api.routes.auth.create_refresh_token')
@patch('mash.services.api.routes.auth.create_access_token')
@patch('mash.services.api.routes.auth.get_user_by_email')
@patch('mash.services.api.routes.auth.email_in_whitelist')
@patch('mash.services.api.routes.auth.jwt')
@patch('mash.services.api.routes.auth.OAuth2Session')
@patch('mash.services.api.routes.auth.current_app')
def test_oauth2_login(
        mock_current_app,
        mock_oauth2_session,
        mock_jwt,
        mock_email_in_whitelist,
        mock_get_user_by_email,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_add_token_to_database,
        test_client
):
    mock_current_app.config = {
        'AUTH_METHOD': 'oauth2',
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
    mock_jwt.decode.return_value = {'email': 'user1@fake.com'}
    mock_email_in_whitelist.return_value = False
    user = Mock()
    user.username = 'user1'
    mock_get_user_by_email.return_value = user

    response = test_client.post(
        '/auth/oauth2',
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
        '/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_add_token_to_database.assert_has_calls([
        call(access_token, 'user1'),
        call(refresh_token, 'user1')
    ])

    assert response.status_code == 200
    assert response.json['access_token'] == '54321'
    assert response.json['refresh_token'] == '12345'

    mock_current_app.config = {'AUTH_METHOD': 'password'}

    response = test_client.post(
        '/auth/oauth2',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 403
