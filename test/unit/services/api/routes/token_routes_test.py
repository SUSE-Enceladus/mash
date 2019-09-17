from unittest.mock import patch, Mock


@patch('mash.services.api.routes.token.add_token_to_database')
@patch('mash.services.api.routes.token.create_access_token')
@patch('mash.services.api.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_refresh_token_in_request')
def test_api_refresh_token(
        mock_jwt_required,
        mock_jwt_identity,
        mock_create_access_token,
        mock_add_token_to_database,
        test_client
):
    access_token = '54321'
    mock_create_access_token.return_value = access_token
    mock_jwt_identity.return_value = 'user1'

    response = test_client.post('/auth/token/refresh')

    mock_add_token_to_database.assert_called_once_with('54321', 'user1')

    assert response.status_code == 200
    assert response.data == b'{"access_token":"54321"}\n'


@patch('mash.services.api.routes.token.get_user_tokens')
@patch('mash.services.api.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_token_list(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_user_tokens,
        test_client
):
    access_token = Mock()
    access_token.id = '1'
    access_token.jti = '54321'
    access_token.token_type = 'access'
    access_token.expires = None

    mock_get_user_tokens.return_value = [access_token]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/auth/token')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['jti'] == "54321"
    assert response.json[0]['token_type'] == "access"


@patch('mash.services.api.routes.token.revoke_tokens')
@patch('mash.services.api.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_tokens(
        mock_jwt_required,
        mock_jwt_identity,
        mock_revoke_tokens,
        test_client
):
    mock_jwt_identity.return_value = 'user1'
    mock_revoke_tokens.return_value = 5

    response = test_client.delete('/auth/token')

    mock_revoke_tokens.assert_called_once_with('user1')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Successfully deleted 5 tokens"}\n'


@patch('mash.services.api.routes.token.revoke_token_by_jti')
@patch('mash.services.api.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_token(
        mock_jwt_required,
        mock_jwt_identity,
        mock_revoke_token,
        test_client
):
    mock_jwt_identity.return_value = 'user1'
    mock_revoke_token.return_value = 1

    response = test_client.delete('/auth/token/54321')

    mock_revoke_token.assert_called_once_with('54321', 'user1')

    assert response.status_code == 200
    assert response.data == b'{"msg":"Token revoked"}\n'

    # Not found
    mock_revoke_token.return_value = 0
    response = test_client.delete('/auth/token/54321')

    assert response.status_code == 404
    assert response.data == b'{"msg":"Token not found"}\n'


@patch('mash.services.api.routes.token.get_token_by_jti')
@patch('mash.services.api.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_token(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_token,
        test_client
):
    access_token = Mock()
    access_token.id = '1'
    access_token.jti = '54321'
    access_token.token_type = 'access'
    access_token.expires = None
    mock_get_token.return_value = access_token
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/auth/token/54321')

    mock_get_token.assert_called_once_with('54321', 'user1')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['jti'] == "54321"
    assert response.json['token_type'] == "access"

    # Not found
    mock_get_token.return_value = None
    response = test_client.get('/auth/token/54321')

    assert response.status_code == 404
    assert response.data == b'{"msg":"Token not found"}\n'
