import json

from sqlalchemy.orm.exc import NoResultFound
from unittest.mock import patch, Mock


@patch('mash.services.database.utils.tokens.db')
def test_api_add_token(
    mock_db,
    test_client
):
    data = {
        'jti': '54321',
        'token_type': 'refresh',
        'user_id': '1',
        'expires': 1566501990
    }

    response = test_client.post(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert mock_db.session.add.call_count == 1
    assert mock_db.session.commit.call_count == 1
    assert response.status_code == 201
    assert response.data == b'{"msg":"User token added."}\n'

    # Test exception adding token
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to add user token: Broken"}\n'


@patch('mash.services.database.utils.tokens.get_user_by_id')
def test_api_token_list(
    mock_get_user,
    test_client
):
    access_token = Mock()
    access_token.id = '1'
    access_token.jti = '54321'
    access_token.token_type = 'access'
    access_token.expires = None

    user = Mock()
    user.tokens = [access_token]
    mock_get_user.return_value = user

    response = test_client.get('/tokens/list/1')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['jti'] == "54321"
    assert response.json[0]['token_type'] == "access"


@patch('mash.services.database.utils.tokens.get_token_by_jti')
@patch('mash.services.database.utils.tokens.db')
def test_api_delete_token(
    mock_db,
    mock_get_token,
    test_client
):
    token = Mock()
    mock_get_token.return_value = token

    data = {
        'jti': '54321',
        'user_id': '1'
    }

    response = test_client.delete(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_db.session.delete.assert_called_once_with(token)
    mock_db.session.commit.assert_called_once_with()

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # No token
    mock_get_token.return_value = None
    response = test_client.delete(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.tokens.get_user_by_id')
@patch('mash.services.database.utils.tokens.db')
def test_api_delete_tokens(
    mock_db,
    mock_get_user,
    test_client
):
    user = Mock()
    token = Mock()
    user.tokens = [token]
    mock_get_user.return_value = user

    response = test_client.delete('/tokens/list/1')

    mock_db.session.commit.assert_called_once_with()
    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'


@patch('mash.services.database.utils.tokens.Token')
def test_api_get_token(
    mock_token,
    test_client
):
    access_token = Mock()
    access_token.id = '1'
    access_token.jti = '54321'
    access_token.token_type = 'access'
    access_token.expires = None
    queryset = Mock()
    queryset.one.return_value = access_token
    mock_token.query.filter_by.return_value = queryset

    data = {
        'jti': '54321',
        'user_id': '1'
    }

    response = test_client.get(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['jti'] == "54321"
    assert response.json['token_type'] == "access"

    # No token found
    queryset.one.side_effect = NoResultFound()
    response = test_client.get(
        '/tokens/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert not response.json
