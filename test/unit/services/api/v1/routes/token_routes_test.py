from unittest.mock import patch, Mock


@patch('mash.services.api.v1.utils.tokens.handle_request')
@patch('mash.services.api.v1.utils.tokens.decode_token')
@patch('mash.services.api.v1.routes.token.create_access_token')
@patch('mash.services.api.v1.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_refresh_token(
    mock_jwt_required,
    mock_jwt_identity,
    mock_create_access_token,
    mock_decode_token,
    mock_handle_request,
    test_client
):
    access_token = 'encodedtoken'
    mock_create_access_token.return_value = access_token
    mock_jwt_identity.return_value = 'user1'

    decoded_token = {
        'jti': '123',
        'type': 'access',
        'exp': 1566501990
    }
    mock_decode_token.return_value = decoded_token

    response = test_client.post('/v1/auth/token/refresh')
    mock_handle_request.assert_called_once_with(
        'http://localhost:5057/',
        'tokens/',
        'post',
        job_data={
            'jti': '123',
            'token_type': 'access',
            'user_id': 'user1',
            'expires': 1566501990
        }
    )

    assert response.status_code == 200
    assert response.data == b'{"access_token":"encodedtoken"}\n'


@patch('mash.services.api.v1.utils.tokens.handle_request')
@patch('mash.services.api.v1.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_token_list(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    access_token = {
        'id': '1',
        'jti': '54321',
        'token_type': 'access'
    }
    response = Mock()
    response.json.return_value = [access_token]
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/v1/auth/token')

    assert result.status_code == 200
    assert result.json[0]['id'] == "1"
    assert result.json[0]['jti'] == "54321"
    assert result.json[0]['token_type'] == "access"


@patch('mash.services.api.v1.utils.tokens.handle_request')
@patch('mash.services.api.v1.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_tokens(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    response = Mock()
    response.json.return_value = {'rows_deleted': 5}
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/v1/auth/token')

    assert result.status_code == 200
    assert result.data == b'{"msg":"Successfully deleted 5 tokens"}\n'


@patch('mash.services.api.v1.utils.tokens.handle_request')
@patch('mash.services.api.v1.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_token(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/v1/auth/token/54321')

    assert result.status_code == 200
    assert result.data == b'{"msg":"Token revoked"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}
    result = test_client.delete('/v1/auth/token/54321')

    assert result.status_code == 404
    assert result.data == b'{"msg":"Token not found"}\n'


@patch('mash.services.api.v1.utils.tokens.handle_request')
@patch('mash.services.api.v1.routes.token.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_token(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    access_token = {
        'id': '1',
        'jti': '54321',
        'token_type': 'access'
    }
    response = Mock()
    response.json.return_value = access_token
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/v1/auth/token/54321')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['jti'] == "54321"
    assert result.json['token_type'] == "access"

    # Not found
    response.json.return_value = {}
    result = test_client.get('/v1/auth/token/54321')

    assert result.status_code == 404
    assert result.data == b'{"msg":"Token not found"}\n'
