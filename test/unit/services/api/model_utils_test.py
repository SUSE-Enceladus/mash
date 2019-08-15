from unittest.mock import patch, Mock

from sqlalchemy.exc import IntegrityError

with patch('mash.services.base_config.BaseConfig') as mock_config:
    config = Mock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    from mash.services.api.model_utils import (
        add_user,
        verify_login,
        get_user_by_username,
        get_user_email,
        delete_user
    )


@patch('mash.services.api.model_utils.db')
def test_add_user(mock_db):
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user.username == 'user1'
    assert user.email == 'user1@fake.com'

    mock_db.session.commit.side_effect = IntegrityError(
        'Duplicate', None, None
    )
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user is None
    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.model_utils.get_user_by_username')
def test_verify_login(mock_get_user):
    user = Mock()
    user.check_password.side_effect = [True, False]
    mock_get_user.return_value = user

    assert verify_login('user1', 'password123') == user
    assert verify_login('user1', 'password321') is None


@patch('mash.services.api.model_utils.User')
def test_get_user_by_username(mock_user):
    user = Mock()
    queryset = Mock()
    queryset.first.return_value = user
    mock_user.query.filter_by.return_value = queryset

    assert get_user_by_username('user1') == user


@patch('mash.services.api.model_utils.get_user_by_username')
def test_get_user_email(mock_get_user):
    user = Mock()
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user

    assert get_user_email('user1') == 'user1@fake.com'


@patch('mash.services.api.model_utils.db')
@patch('mash.services.api.model_utils.get_user_by_username')
def test_delete_user(mock_get_user, mock_db):
    user = Mock()
    mock_get_user.return_value = user

    assert delete_user('user1') == 1
    mock_db.session.delete.assert_called_once_with(user)

    mock_get_user.return_value = None
    assert delete_user('user1') == 0
