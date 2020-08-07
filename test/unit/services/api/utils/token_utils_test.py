from unittest.mock import patch
from mash.services.api.app import check_if_token_in_blacklist


@patch('mash.services.api.utils.tokens.get_token_by_jti')
def test_check_if_token_in_blacklist(mock_get_token):
    decoded_token = {'jti': '123', 'identity': 'user1'}
    mock_get_token.return_value = decoded_token

    result = check_if_token_in_blacklist(decoded_token)
    assert result is False

    # Token revoked
    mock_get_token.return_value = None
    result = check_if_token_in_blacklist(decoded_token)
    assert result
