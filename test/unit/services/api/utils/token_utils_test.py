from datetime import datetime
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound

from mash.services.api.app import check_if_token_in_blacklist
from mash.services.api.utils.tokens import (
    add_token_to_database,
    is_token_revoked,
    get_user_tokens,
    get_token_by_jti,
    revoke_token_by_jti,
    revoke_tokens,
    prune_expired_tokens
)


@patch('mash.services.api.utils.tokens.decode_token')
@patch('mash.services.api.utils.tokens.get_user_by_username')
@patch('mash.services.api.utils.tokens.db')
def test_add_token_to_database(mock_db, mock_get_user, mock_decode_token):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    decoded_token = {
        'jti': '123',
        'type': 'access',
        'exp': 1566501990
    }
    mock_decode_token.return_value = decoded_token

    add_token_to_database(Mock(), 'user1')

    assert mock_db.session.add.call_count == 1
    assert mock_db.session.commit.call_count == 1

    # Without expiration

    decoded_token = {'jti': '123', 'type': 'access'}
    mock_decode_token.return_value = decoded_token
    add_token_to_database(Mock(), 'user1')


@patch('mash.services.api.utils.tokens.Token')
def test_is_token_revoked(mock_token):
    decoded_token = {'jti': '123'}

    queryset = Mock()
    queryset.one.side_effect = NoResultFound()
    mock_token.query.filter_by.return_value = queryset

    assert is_token_revoked(decoded_token)


@patch('mash.services.api.utils.tokens.get_user_by_username')
def test_get_user_tokens(mock_get_user):
    user = Mock()
    token = Mock()
    user.tokens = [token]
    mock_get_user.return_value = user

    result = get_user_tokens('user1')
    assert result == [token]


@patch('mash.services.api.utils.tokens.Token')
def test_get_token_by_jti(mock_token):
    token = Mock()
    queryset = Mock()
    queryset.first.return_value = token
    queryset1 = Mock()
    queryset1.filter_by.return_value = queryset
    mock_token.query.filter.return_value = queryset1

    assert get_token_by_jti('123', 'user1') == token


@patch('mash.services.api.utils.tokens.get_token_by_jti')
@patch('mash.services.api.utils.tokens.db')
def test_revoke_token_by_jti(mock_db, mock_get_token):
    token = Mock()
    mock_get_token.return_value = token

    assert revoke_token_by_jti('123', 'user1') == 1
    mock_db.session.delete.assert_called_once_with(token)
    mock_db.session.commit.assert_called_once_with()

    # No token
    mock_get_token.return_value = None
    assert revoke_token_by_jti('123', 'user1') == 0


@patch('mash.services.api.utils.tokens.get_user_by_username')
@patch('mash.services.api.utils.tokens.db')
def test_revoke_tokens(mock_db, mock_get_user):
    user = Mock()
    token = Mock()
    user.tokens = [token]
    mock_get_user.return_value = user

    assert revoke_tokens('user1') == 1
    mock_db.session.commit.assert_called_once_with()


@patch('mash.services.api.utils.tokens.Token')
@patch('mash.services.api.utils.tokens.db')
def test_prune_expired_tokens(mock_db, mock_token):
    queryset = Mock()
    queryset.delete.return_value = 1
    mock_token.query.filter.return_value = queryset
    mock_token.expires = datetime.now()

    assert prune_expired_tokens() == 1
    mock_db.session.commit.assert_called_once_with()


@patch('mash.services.api.app.is_token_revoked')
def test_check_if_token_in_blacklist(mock_is_token_revoked):
    decoded_token = Mock()
    check_if_token_in_blacklist(decoded_token)
    mock_is_token_revoked.assert_called_once_with(decoded_token)
