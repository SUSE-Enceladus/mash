from pytest import raises
from unittest.mock import patch, Mock

from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashDBException
from mash.services.api.utils.users import (
    add_user,
    verify_login,
    get_user_by_username,
    get_user_email,
    delete_user
)


@patch('mash.services.api.utils.users.current_app')
@patch('mash.services.api.utils.users.db')
def test_add_user(mock_db, mock_current_app):
    mock_current_app.config = {
        'EMAIL_WHITELIST': ['user1@fake.com'],
        'DOMAIN_WHITELIST': []
    }
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user.username == 'user1'
    assert user.email == 'user1@fake.com'

    # User duplicate
    mock_db.session.commit.side_effect = IntegrityError(
        'Duplicate', None, None
    )
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user is None
    mock_db.session.rollback.assert_called_once_with()

    # Password too short
    with raises(MashDBException):
        add_user('user1', 'user1@fake.com', 'pass')

    # Not in email whitelist
    mock_current_app.config = {
        'EMAIL_WHITELIST': ['user2@fake.com'],
        'DOMAIN_WHITELIST': []
    }
    with raises(MashDBException):
        add_user('user1', 'user1@fake.com', 'password123')

    # Not in domain whitelist
    mock_current_app.config = {
        'EMAIL_WHITELIST': [],
        'DOMAIN_WHITELIST': ['suse.com']
    }
    with raises(MashDBException):
        add_user('user1', 'user1@fake.com', 'password123')


@patch('mash.services.api.utils.users.get_user_by_username')
def test_verify_login(mock_get_user):
    user = Mock()
    user.check_password.side_effect = [True, False]
    mock_get_user.return_value = user

    assert verify_login('user1', 'password123') == user
    assert verify_login('user1', 'password321') is None


@patch('mash.services.api.utils.users.User')
def test_get_user_by_username(mock_user):
    user = Mock()
    queryset = Mock()
    queryset.first.return_value = user
    mock_user.query.filter_by.return_value = queryset

    assert get_user_by_username('user1') == user


@patch('mash.services.api.utils.users.get_user_by_username')
def test_get_user_email(mock_get_user):
    user = Mock()
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user

    assert get_user_email('user1') == 'user1@fake.com'


@patch('mash.services.api.utils.users.db')
@patch('mash.services.api.utils.users.get_user_by_username')
def test_delete_user(mock_get_user, mock_db):
    user = Mock()
    mock_get_user.return_value = user

    assert delete_user('user1') == 1
    mock_db.session.delete.assert_called_once_with(user)

    mock_get_user.return_value = None
    assert delete_user('user1') == 0
