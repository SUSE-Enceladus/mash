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
from mash.utils.ec2 import (
    get_client,
    get_vpc_id_from_subnet,
    share_image_snapshot,
    cleanup_ec2_image
)


@patch('mash.utils.ec2.boto3')
def test_get_client(mock_boto3):
    client = Mock()
    session = Mock()
    session.client.return_value = client
    mock_boto3.session.Session.return_value = session

    result = get_client('ec2', '123456', 'abc123', 'us-east-1')

    assert client == result
    session.client.assert_called_once_with(
        service_name='ec2',
        aws_access_key_id='123456',
        aws_secret_access_key='abc123',
        region_name='us-east-1',
    )


def test_get_vpc_id_from_subnet():
    client = Mock()
    client.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123456789'}]}
    assert get_vpc_id_from_subnet(client, 'subnet-123456789') == 'vpc-123456789'
    client.describe_subnets.assert_called_once_with(SubnetIds=['subnet-123456789'])


@patch('mash.utils.ec2.get_client')
def test_share_image_snapshot(mock_get_client):
    images = {
        'Images': [{
            'Name': 'test',
            'BlockDeviceMappings': [{'Ebs': {'SnapshotId': '123'}}]}
        ]
    }
    client = Mock()
    mock_get_client.return_value = client
    client.describe_images.return_value = images

    share_image_snapshot('test', '123,321', 'us-east-1', '123', '321')

    client.modify_snapshot_attribute.assert_called_once_with(
        Attribute='createVolumePermission',
        OperationType='add',
        SnapshotId='123',
        UserIds=['123', '321']
    )


@patch('mash.utils.ec2.EC2RemoveImage')
def test_cleanup_images(mock_rm_img):
    log_callback = Mock()
    rm_img = Mock()
    rm_img.remove_images.side_effect = Exception('image not found!')
    mock_rm_img.return_value = rm_img

    cleanup_ec2_image('123', '321', log_callback, 'us-east-1', 'ami-123')

    log_callback.warning.assert_called_once_with(
        'Failed to cleanup image: image not found!'
    )
    rm_img.set_region.assert_called_once_with('us-east-1')
    rm_img.remove_images.assert_called_once_with()
