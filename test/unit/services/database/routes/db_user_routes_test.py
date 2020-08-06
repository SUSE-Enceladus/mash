import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock


@patch('mash.services.database.utils.users.db')
def test_add_user(mock_db, test_client):
    data = {
        'email': 'user1@fake.com',
        'password': 'secretpassword123'
    }
    result = test_client.post(
        '/users/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 201
    assert result.json['email'] == "user1@fake.com"
    mock_db.session.commit.assert_called_once_with()

    # User exists
    mock_db.session.commit.side_effect = IntegrityError(
        'Already exists',
        None,
        None
    )

    result = test_client.post(
        '/users/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 201
    assert result.data == b'{}\n'

    # No password (OIDC)
    data['password'] = None
    mock_db.session.commit.side_effect = None
    result = test_client.post(
        '/users/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 201
    assert result.json['email'] == "user1@fake.com"


@patch('mash.services.database.utils.users.User')
def test_get_user(mock_user, test_client):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    queryset = Mock()
    queryset.first.return_value = user
    mock_user.query.filter_by.return_value = queryset

    result = test_client.get('/users/1')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['email'] == "user1@fake.com"


@patch('mash.services.database.utils.users.add_new_user')
@patch('mash.services.database.utils.users.User')
def test_get_or_create_user(mock_user, mock_add_user, test_client):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    mock_add_user.return_value = user

    queryset = Mock()
    queryset.first.return_value = None
    mock_user.query.filter_by.return_value = queryset

    result = test_client.get(
        '/users/get_user/user1@fake.com',
        content_type='application/json',
        data=json.dumps({'create': True}, sort_keys=True)
    )

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['email'] == "user1@fake.com"


@patch('mash.services.database.utils.users.get_user_by_email')
def test_validate_login(mock_get_user, test_client):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    user.password_dirty = False
    user.check_password.return_value = True
    mock_get_user.return_value = user

    data = {
        'email': 'user1@fake.com',
        'password': 'supersecret123'
    }

    result = test_client.post(
        '/users/login/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['email'] == "user1@fake.com"

    # Password dirty
    user.password_dirty = True

    result = test_client.post(
        '/users/login/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 403

    # Password incorrect
    user.password_dirty = False
    user.check_password.return_value = False

    result = test_client.post(
        '/users/login/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 200
    assert result.json == {}


@patch('mash.services.database.utils.users.handle_request')
@patch('mash.services.database.utils.users.db')
@patch('mash.services.database.utils.users.get_user_by_id')
def test_delete_user(mock_get_user, mock_db, mock_handle_request, test_client):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user

    result = test_client.delete('/users/1')

    assert result.status_code == 200
    assert result.data == b'{"msg":"User deleted."}\n'
    mock_db.session.delete.assert_called_once_with(user)
    mock_db.session.commit.assert_called_once_with()

    # Not found
    mock_get_user.return_value = None
    result = test_client.delete('/users/1')

    assert result.status_code == 404
    assert result.data == b'{"msg":"Unable to delete user: 1"}\n'


@patch('mash.services.database.utils.users.db')
@patch('mash.services.database.utils.users.get_user_by_email')
def test_password_reset(
    mock_get_user,
    mock_db,
    test_client
):
    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user

    result = test_client.post(
        '/users/password/reset/user1@fake.com'
    )

    assert result.status_code == 200
    assert b'{"password":"' in result.data
    mock_db.session.commit.assert_called_once_with()
    assert user.password_dirty is True

    # Not found
    mock_get_user.return_value = None
    result = test_client.post(
        '/users/password/reset/user1@fake.com'
    )

    assert result.status_code == 404
    assert result.data == \
        b'{"msg":"Unable to reset user password for user1@fake.com"}\n'


@patch('mash.services.database.utils.users.db')
@patch('mash.services.database.utils.users.get_user_by_email')
def test_password_change(
    mock_get_user,
    mock_db,
    test_client
):
    data = {
        'current_password': 'pass',
        'new_password': 'betterpassword'
    }

    user = Mock()
    user.id = '1'
    user.email = 'user1@fake.com'
    user.check_password.return_value = True
    mock_get_user.return_value = user

    result = test_client.post(
        '/users/password/change/user1@fake.com',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 200
    assert result.data == b'{"msg":"Password changed"}\n'
    mock_db.session.commit.assert_called_once_with()
    assert user.password_dirty is False

    # Not found
    mock_get_user.return_value = None
    result = test_client.post(
        '/users/password/change/user1@fake.com',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert result.status_code == 403
    assert result.data == \
        b'{"msg":"Unable to change user password for user1@fake.com"}\n'
