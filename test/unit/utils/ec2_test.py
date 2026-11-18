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
import os

from pytest import raises
from unittest.mock import Mock, patch
from mash.utils.ec2 import (
    create_ssh_security_group,
    get_client,
    get_vpc_id_from_subnet,
    setup_ec2_networking,
    cleanup_ec2_image,
    cleanup_all_ec2_images,
    get_image,
    image_exists,
    get_session,
    download_file_from_s3_bucket
)
from mash.mash_exceptions import MashEc2UtilsException


# Test Cases
@patch('mash.utils.ec2.boto3')
def test_get_session(mock_boto3):
    session = Mock()
    mock_boto3.Session.return_value = session

    result = get_session('123456', 'abc123', 'us-east-1')

    assert session == result


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


@patch('mash.utils.ec2.generate_name')
def test_create_ssh_security_group(mock_generate_name):
    mock_generate_name.return_value = 'abcdefgh'
    client = Mock()
    client.create_security_group.return_value = {'GroupId': 'sg-123'}

    assert create_ssh_security_group(client, 'vpc-123') == 'sg-123'

    client.create_security_group.assert_called_once_with(
        GroupName='mash-abcdefgh',
        Description='mash temporary ssh access',
        VpcId='vpc-123'
    )
    client.authorize_security_group_ingress.assert_called_once_with(
        GroupId='sg-123',
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )


@patch('mash.utils.ec2.get_vpc_id_from_subnet')
@patch('mash.utils.ec2.get_key_from_file')
@patch('mash.utils.ec2.generate_name')
@patch('mash.utils.ec2.get_client')
@patch('mash.utils.ec2.EC2Setup')
def test_setup_ec2_networking_new_vpc(
    mock_ec2_setup,
    mock_get_client,
    mock_generate_name,
    mock_get_key_from_file,
    mock_get_vpc_id_from_subnet
):
    client = Mock()
    client.create_security_group.return_value = {'GroupId': 'sg-123'}
    mock_get_client.return_value = client
    mock_generate_name.return_value = 'random'
    mock_get_key_from_file.return_value = 'fakekey'

    ec2_setup = Mock()
    ec2_setup.create_vpc_subnet.return_value = 'subnet-123'
    ec2_setup.vpc_id = 'vpc-123'
    mock_ec2_setup.return_value = ec2_setup

    manager = Mock()
    manager.attach_mock(client.delete_key_pair, 'delete_key_pair')
    manager.attach_mock(client.delete_security_group, 'delete_sg')
    manager.attach_mock(ec2_setup.clean_up, 'clean_up')

    with setup_ec2_networking('key', 'us-east-1', 'secret', 'file') as net:
        assert net == {
            'ssh_key_name': 'random',
            'subnet_id': 'subnet-123',
            'security_group_id': 'sg-123'
        }

    mock_ec2_setup.assert_called_once_with(
        access_key='key',
        region='us-east-1',
        secret_key='secret',
        session_token=None
    )
    assert not mock_get_vpc_id_from_subnet.called
    assert client.create_security_group.call_args[1]['VpcId'] == 'vpc-123'
    client.import_key_pair.assert_called_once_with(
        KeyName='random',
        PublicKeyMaterial='fakekey'
    )
    # Security group has to go before the vpc is removed
    assert [c[0] for c in manager.mock_calls] == [
        'delete_key_pair', 'delete_sg', 'clean_up'
    ]
    client.delete_security_group.assert_called_once_with(GroupId='sg-123')


@patch('mash.utils.ec2.get_vpc_id_from_subnet')
@patch('mash.utils.ec2.get_key_from_file')
@patch('mash.utils.ec2.generate_name')
@patch('mash.utils.ec2.get_client')
@patch('mash.utils.ec2.EC2Setup')
def test_setup_ec2_networking_existing_subnet(
    mock_ec2_setup,
    mock_get_client,
    mock_generate_name,
    mock_get_key_from_file,
    mock_get_vpc_id_from_subnet
):
    client = Mock()
    client.create_security_group.return_value = {'GroupId': 'sg-123'}
    mock_get_client.return_value = client
    mock_get_vpc_id_from_subnet.return_value = 'vpc-456'
    ec2_setup = mock_ec2_setup.return_value

    with setup_ec2_networking(
        'key', 'us-east-1', 'secret', 'file', subnet_id='subnet-456'
    ) as net:
        assert net['subnet_id'] == 'subnet-456'
        assert net['security_group_id'] == 'sg-123'

    assert not ec2_setup.create_vpc_subnet.called
    assert client.create_security_group.call_args[1]['VpcId'] == 'vpc-456'
    client.delete_security_group.assert_called_once_with(GroupId='sg-123')
    ec2_setup.clean_up.assert_called_once_with()


@patch('mash.utils.ec2.get_key_from_file')
@patch('mash.utils.ec2.generate_name')
@patch('mash.utils.ec2.get_client')
@patch('mash.utils.ec2.EC2Setup')
def test_setup_ec2_networking_cleanup_on_error(
    mock_ec2_setup,
    mock_get_client,
    mock_generate_name,
    mock_get_key_from_file
):
    client = Mock()
    client.create_security_group.return_value = {'GroupId': 'sg-123'}
    # A failing step must not skip the remaining cleanup
    client.delete_key_pair.side_effect = Exception('boom')
    mock_get_client.return_value = client
    ec2_setup = mock_ec2_setup.return_value

    with raises(RuntimeError):
        with setup_ec2_networking('key', 'us-east-1', 'secret', 'file'):
            raise RuntimeError('test failed')

    client.delete_security_group.assert_called_once_with(GroupId='sg-123')
    ec2_setup.clean_up.assert_called_once_with()


@patch('mash.utils.ec2.get_key_from_file')
@patch('mash.utils.ec2.generate_name')
@patch('mash.utils.ec2.get_client')
@patch('mash.utils.ec2.EC2Setup')
def test_setup_ec2_networking_sg_not_created(
    mock_ec2_setup,
    mock_get_client,
    mock_generate_name,
    mock_get_key_from_file
):
    client = Mock()
    client.create_security_group.side_effect = Exception('denied')
    mock_get_client.return_value = client
    ec2_setup = mock_ec2_setup.return_value

    with raises(Exception, match='denied'):
        with setup_ec2_networking('key', 'us-east-1', 'secret', 'file'):
            pass  # pragma: no cover

    assert not client.delete_security_group.called
    ec2_setup.clean_up.assert_called_once_with()


@patch('mash.utils.ec2.EC2RemoveImage')
def test_cleanup_images(mock_rm_img):
    log_callback = Mock()
    rm_img = Mock()
    mock_rm_img.return_value = rm_img

    cleanup_ec2_image('123', '321', log_callback, 'us-east-1', 'ami-123')

    rm_img.set_region.assert_called_once_with('us-east-1')
    rm_img.remove_images.assert_called_once_with()

    # Cleanup by name
    cleanup_ec2_image(
        '123',
        '321',
        log_callback,
        'us-east-1',
        image_name='image name'
    )

    # No image id or name provided
    with raises(MashEc2UtilsException):
        cleanup_ec2_image(
            '123',
            '321',
            log_callback,
            'us-east-1'
        )


@patch('mash.utils.ec2.cleanup_ec2_image')
def test_cleanup_all_ec2_images(mock_cleanup_image):
    log = Mock()
    regions = ['us-east-1']
    mock_cleanup_image.side_effect = Exception('Failed')

    cleanup_all_ec2_images('123', '321', log, regions, 'image name 123')
    log.warning.assert_called_once_with(
        'Failed to cleanup image: Failed'
    )


@patch('mash.utils.ec2.describe_images')
def test_get_image(mock_describe_images):
    client = Mock()
    image = {'Name': 'image name 123'}

    mock_describe_images.side_effect = [
        [image],
        [image, image],
        []
    ]

    # One image found
    result = get_image(client, 'image name 123')
    assert result == image

    # multiple images found
    with raises(MashEc2UtilsException):
        get_image(client, 'image name 123')

    # No image found
    result = get_image(client, 'image name 123')
    assert result is None


@patch('mash.utils.ec2.get_image')
def test_image_exists(mock_get_image):
    client = Mock()
    image = {'Name': 'image name 123'}
    mock_get_image.side_effect = [image, None]

    assert image_exists(client, 'image name 123')
    assert not image_exists(client, 'image name 321')


@patch('mash.utils.ec2.os.path.exists')
def test_download_file_from_s3_bucket(os_path_exists_mock):

    os_path_exists_mock.return_value = True

    s3_client_mock = Mock()
    s3_client_mock.download_file.return_value = True
    boto3_session_mock = Mock()
    boto3_session_mock.client.return_value = s3_client_mock

    tests_parameters = [
        (
            'my_bucket_name',
            '/obj_key/my_file_name',
            '/my/download/directory/my_file_name'
        )
    ]

    for bucket_name, object_key, download_path in tests_parameters:
        download_file_from_s3_bucket(
            boto3_session_mock,
            bucket_name,
            object_key,
            download_path
        )
        boto3_session_mock.client.assert_called_once_with(service_name='s3')
        s3_client_mock.download_file.assert_called_once_with(
            bucket_name,
            object_key,
            download_path
        )

        directory_name, file_name = os.path.split(download_path)
        os_path_exists_mock.assert_called_once_with(directory_name)
        os_path_exists_mock.reset_mock()
        boto3_session_mock.reset_mock()
        s3_client_mock.reset_mock()


@patch('mash.utils.ec2.os.makedirs')
@patch('mash.utils.ec2.os.path.exists')
def test_download_file_from_s3_bucket_non_existing_directory(
    os_path_exists_mock,
    os_makedirs_mock
):

    os_path_exists_mock.return_value = False
    os_makedirs_mock.return_value = True

    s3_client_mock = Mock()
    s3_client_mock.download_file.return_value = True
    boto3_session_mock = Mock()
    boto3_session_mock.client.return_value = s3_client_mock

    tests_parameters = [
        (
            'my_bucket_name',
            '/my_obj_key/my_file_name',
            '/my/directory/name/my_destination_filename'
        )
    ]

    for bucket_name, obj_key, download_path in tests_parameters:
        download_file_from_s3_bucket(
            boto3_session_mock,
            bucket_name,
            obj_key,
            download_path
        )
        boto3_session_mock.client.assert_called_once_with(service_name='s3')
        s3_client_mock.download_file.assert_called_once_with(
            bucket_name,
            obj_key,
            download_path
        )
        directory_name, file_name = os.path.split(download_path)
        os_path_exists_mock.assert_called_once_with(directory_name)
        os_makedirs_mock.assert_called_once_with(directory_name)
        os_path_exists_mock.reset_mock()
        boto3_session_mock.reset_mock()
        s3_client_mock.reset_mock()
