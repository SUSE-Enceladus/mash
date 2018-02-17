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

from unittest.mock import Mock, patch
from mash.utils.ec2 import get_client


@patch('mash.utils.ec2.boto3')
def test_get_client(mock_boto3):
    client = Mock()

    mock_boto3.client.return_value = client
    result = get_client('ec2', '123456', 'abc123', 'us-east-1')

    assert client == result
    mock_boto3.client.assert_called_once_with(
        service_name='ec2',
        aws_access_key_id='123456',
        aws_secret_access_key='abc123',
        region_name='us-east-1',
    )
