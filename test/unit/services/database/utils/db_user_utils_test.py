from unittest.mock import patch, Mock

from mash.services.database.utils.users import (
    get_user_by_id
)


@patch('mash.services.database.utils.users.User')
def test_get_user_by_id(mock_user):
    user = Mock()
    queryset = Mock()
    queryset.first.return_value = user
    mock_user.query.filter_by.return_value = queryset

    assert get_user_by_id(1) == user
