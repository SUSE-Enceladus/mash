# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

import io

from unittest.mock import MagicMock, patch
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import (
    create_json_file,
    generate_name,
    get_key_from_file
)


@patch('mash.utils.mash_utils.os')
@patch('mash.utils.mash_utils.NamedTemporaryFile')
def test_create_json_file(mock_temp_file, mock_os):
    json_file = MagicMock()
    json_file.name = 'test.json'
    mock_temp_file.return_value = json_file

    data = {'tenantId': '123456', 'subscriptionId': '98765'}
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        with create_json_file(data) as json_file:
            assert json_file == 'test.json'

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(JsonFormat.json_message(data))

    mock_os.remove.assert_called_once_with('test.json')


def test_generate_name():
    result = generate_name(10)
    assert len(result) == 10


def test_get_key_from_file():
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.return_value = 'fakekey'
        result = get_key_from_file('my-key.file')

    assert result == 'fakekey'
