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
    get_client,
    get_vpc_id_from_subnet,
    cleanup_ec2_image,
    cleanup_all_ec2_images,
    get_image,
    image_exists,
    get_session,
    get_file_list_from_s3_bucket,
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


def test_get_file_list_from_s3_bucket():

    response_iterator = [
        {
            'Contents': [
                {
                    'Key': 'file_name_1.tar.gz'
                },
                {
                    'Key': 'file_name_2.tar.gz'
                },
                {
                    'Key': 'another_file_name_1.tar.gz'
                }
            ]
        },
        {
            'Contents': [
                {
                    'Key': 'file_name_5.tar.gz'
                },
                {
                    'Key': 'file_name_22.tar.gz'
                },
                {
                    'Key': 'yet_another_file_name_1.tar.gz'
                }
            ]
        }
    ]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = response_iterator
    s3_client_mock = Mock()
    s3_client_mock.get_paginator.return_value = paginator_mock
    boto3_session_mock = Mock()
    boto3_session_mock.client.return_value = s3_client_mock

    tests_parameters = [
        (
            'my_bucket_name',
            '',
            [
                'file_name_1.tar.gz',
                'file_name_2.tar.gz',
                'another_file_name_1.tar.gz',
                'file_name_5.tar.gz',
                'file_name_22.tar.gz',
                'yet_another_file_name_1.tar.gz'
            ]
        ),
        (
            'my_bucket_name',
            r'^file_name_\d\.tar\.gz$',
            [
                'file_name_1.tar.gz',
                'file_name_2.tar.gz',
                'file_name_5.tar.gz',
            ]
        ),
    ]

    for bucket_name, regex, expected_output in tests_parameters:
        assert expected_output == \
            get_file_list_from_s3_bucket(
                boto3_session_mock,
                bucket_name,
                regex
            )
        boto3_session_mock.client.assert_called_once_with(service_name='s3')
        s3_client_mock.get_paginator.assert_called_once_with('list_objects_v2')
        paginator_mock.paginate.assert_called_once_with(Bucket=bucket_name)
        paginator_mock.reset_mock()
        boto3_session_mock.reset_mock()
        s3_client_mock.reset_mock()


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
