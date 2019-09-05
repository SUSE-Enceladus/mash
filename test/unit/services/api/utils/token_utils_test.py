from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound

from mash.services.api.app import check_if_token_in_blacklist
from mash.services.api.utils.tokens import is_token_revoked


@patch('mash.services.api.utils.tokens.Token')
def test_is_token_revoked(mock_token):
    decoded_token = {'jti': '123'}

    queryset = Mock()
    queryset.one.side_effect = NoResultFound()
    mock_token.query.filter_by.return_value = queryset

    assert is_token_revoked(decoded_token)


@patch('mash.services.api.app.is_token_revoked')
def test_check_if_token_in_blacklist(mock_is_token_revoked):
    decoded_token = Mock()
    check_if_token_in_blacklist(decoded_token)
    mock_is_token_revoked.assert_called_once_with(decoded_token)
