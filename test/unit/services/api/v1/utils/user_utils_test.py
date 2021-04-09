from pytest import raises
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.api.v1.utils.users import add_user

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
def test_add_user_not_in_whitelist(mock_get_current_object):
    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {
        'EMAIL_WHITELIST': ['user1@fake.com'],
        'DOMAIN_WHITELIST': []
    }

    # Not in email whitelist
    app.config = {
        'EMAIL_WHITELIST': ['user2@fake.com'],
        'DOMAIN_WHITELIST': []
    }
    with raises(MashException):
        add_user('user1@fake.com', 'password123')

    # Not in domain whitelist
    app.config = {
        'EMAIL_WHITELIST': [],
        'DOMAIN_WHITELIST': ['suse.com']
    }
    with raises(MashException):
        add_user('user1@fake.com', 'password123')
