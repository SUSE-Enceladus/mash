import json

from unittest.mock import patch, call


@patch('mash.services.api.routes.auth.add_token_to_database')
@patch('mash.services.api.routes.auth.create_refresh_token')
@patch('mash.services.api.routes.auth.create_access_token')
@patch('mash.services.api.routes.auth.verify_login')
def test_api_login(
        mock_verify_login,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_add_token_to_database,
        test_client
):
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
