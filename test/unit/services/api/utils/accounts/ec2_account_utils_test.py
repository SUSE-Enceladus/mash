# Copyright (c) 2019 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

from unittest.mock import patch, Mock

from mash.services.api.utils.accounts.ec2 import get_accounts_in_ec2_group

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.ec2.handle_request')
def test_get_ec2_group(mock_handle_request, mock_get_current_object):
    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'DATABASE_API_URL': 'http://localhost:5000/'}

    response = Mock()
    response.json.return_value = ['acnt1']
    mock_handle_request.return_value = response

    assert get_accounts_in_ec2_group('group1', 1) == ['acnt1']
