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
import json
import os

from pytest import raises
from unittest.mock import Mock, patch, call
from mash.utils.ec2 import (
    get_client,
    get_vpc_id_from_subnet,
    cleanup_ec2_image,
    cleanup_all_ec2_images,
    get_image,
    image_exists,
    start_mp_change_set,
    create_add_version_change_doc,
    create_restrict_version_change_doc,
    get_delivery_option_id,
    get_session,
    get_file_list_from_s3_bucket,
    download_file_from_s3_bucket
)
from mash.mash_exceptions import MashEc2UtilsException
import botocore.session
import botocore.errorfactory

# botocore ClientExceptionFactory
model = botocore.session.get_session().get_service_model('marketplace-catalog')
factory = botocore.errorfactory.ClientExceptionsFactory()
exceptions = factory.create_client_exceptions(model)

# Mock calls parameters
get_client_args = (
    'marketplace-catalog',
    '123456',
    '654321',
    'us-east-1'
)
data = {
    'ChangeType': 'AddDeliveryOptions',
    'Entity': {
        'Type': 'AmiProduct@1.0',
        'Identifier': '123'
    }
}
details = {
    'Version': {
        'VersionTitle': 'New image',
        'ReleaseNotes': 'Release Notes'
    },
    'DeliveryOptions': [{
        'Details': {
            'AmiDeliveryOptionDetails': {
                'UsageInstructions': 'Login with SSH...',
                'RecommendedInstanceType': 't3.medium',
                'AmiSource': {
                    'AmiId': 'ami-123',
                    'AccessRoleArn': 'arn',
                    'UserName': 'ec2-user',
                    'OperatingSystemName': 'OTHERLINUX',
                    'OperatingSystemVersion': '15.3'
                },
                'SecurityGroups': [{
                    'FromPort': 22,
                    'IpProtocol': 'tcp',
                    'IpRanges': ['0.0.0.0/0'],
                    'ToPort': 22
                }]
            }
        }
    }]
}
data['Details'] = json.dumps(details)
start_changeset_params = {
    'Catalog': 'AWSMarketplace',
    'ChangeSet': [data]
}
describe_changeset_params = {
    'Catalog': 'AWSMarketplace',
    'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
}


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


def test_start_mp_change_set():
    client = Mock()
    client.start_change_set.return_value = {
        'ChangeSetId': '123'
    }

    session = Mock()
    session.client.return_value = client

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    response = start_mp_change_set(
        session,
        [change_set]
    )

    assert response['ChangeSetId'] == '123'
    client.start_change_set.assert_called_once_with(**start_changeset_params)
    session.client.assert_called_once_with('marketplace-catalog')


def test_start_mp_change_set_ongoing_change_ResourceInUseException():

    def generate_exception():
        error_code = 'ResourceInUseException'
        error_message = "Requested change set has entities locked by change sets" \
                        " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                        " change sets: dgoddlepi9nb3ynwrwlkr3be4"
        exc_data = {
            "Error": {
                "Code": error_code,
                "Message": error_message
            },
            "ResponseMetadata": {
                "RequestId": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
                "HTTPStatusCode": 400,
                "HTTPHeaders": {
                    "transfer-encoding": "chunked",
                    "date": "Fri, 01 Jan 2100 00:00:00 GMT",
                    "connection": "close",
                    "server": "AmazonEC2"
                },
                "RetryAttempts": 0
            }
        }

        return exceptions.AccessDeniedException(
            error_response=exc_data,
            operation_name='start_change_set'
        )

    client = Mock()
    client.exceptions.AccessDeniedException = exceptions.AccessDeniedException
    client.start_change_set.side_effect = [
        generate_exception(),
        {
            'ChangeSetId': 'myChangeSetId',
            'ChangeSetArn': 'myChangeSetArn'
        }
    ]

    session = Mock()
    session.client.return_value = client

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    response = start_mp_change_set(
        session,
        change_set=[change_set],
        max_rechecks=10,
        rechecks_period=0,
        conflict_wait_period=0
    )
    assert response.get('ChangeSetId') == 'myChangeSetId'
    # Mock calls assertions
    session.client.assert_has_calls(
        [
            call('marketplace-catalog'),
            call('marketplace-catalog'),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
            call(**start_changeset_params)
        ],
        any_order=True
    )


def test_start_mp_change_set_ongoing_change_GenericBotoException():

    def generate_exception():
        error_code = 'AccessDeniedException'
        error_message = "AccessDeniedException"
        exc_data = {
            "Error": {
                "Code": error_code,
                "Message": error_message
            },
            "ResponseMetadata": {
                "RequestId": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
                "HTTPStatusCode": 400,
                "HTTPHeaders": {
                    "transfer-encoding": "chunked",
                    "date": "Fri, 01 Jan 2100 00:00:00 GMT",
                    "connection": "close",
                    "server": "AmazonEC2"
                },
                "RetryAttempts": 0
            }
        }

        return exceptions.AccessDeniedException(
            error_response=exc_data,
            operation_name='start_change_set'
        )

    client = Mock()
    client.exceptions.AccessDeniedException = exceptions.AccessDeniedException
    client.start_change_set.side_effect = [
        generate_exception(),
        generate_exception(),
        generate_exception()
    ]

    session = Mock()
    session.client.side_effect = [
        client,
        client,
        client,
    ]

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    with raises(Exception) as error:
        start_mp_change_set(
            session,
            change_set=[change_set],
            max_rechecks=10,
            rechecks_period=0,
            conflict_wait_period=0
        )
    assert 'AccessDeniedException' in str(error)

    # Mock calls assertions
    session.client.assert_has_calls(
        [
            call('marketplace-catalog'),
        ],
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
    )


def test_start_mp_change_set_ongoing_change_GenericException():

    def generate_exception():
        return Exception("This is an unexpected exception")

    client = Mock()
    # client.exceptions.AccessDeniedException = exceptions.AccessDeniedException
    client.start_change_set.side_effect = [
        generate_exception(),
        generate_exception(),
        generate_exception()
    ]

    session = Mock()
    session.client.side_effect = [
        client,
        client,
        client,
    ]

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    with raises(Exception) as error:
        start_mp_change_set(
            session,
            change_set=[change_set],
            max_rechecks=10,
            rechecks_period=0,
            conflict_wait_period=0
        )
    assert 'This is an unexpected exception' in str(error)

    # Mock calls assertions
    session.client.assert_has_calls(
        [
            call('marketplace-catalog'),
        ],
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
    )


def test_start_mp_change_set_ongoing_change_ResourceInUseException_3times():

    def generate_exception():
        error_code = 'ResourceInUseException'
        error_message = "Requested change set has entities locked by change sets" \
                        " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                        " change sets: dgoddlepi9nb3ynwrwlkr3be4."
        exc_data = {
            "Error": {
                "Code": error_code,
                "Message": error_message
            },
            "ResponseMetadata": {
                "RequestId": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
                "HTTPStatusCode": 400,
                "HTTPHeaders": {
                    "transfer-encoding": "chunked",
                    "date": "Fri, 01 Jan 2100 00:00:00 GMT",
                    "connection": "close",
                    "server": "AmazonEC2"
                },
                "RetryAttempts": 0
            }
        }

        return exceptions.ResourceInUseException(
            error_response=exc_data,
            operation_name='start_change_set'
        )

    client = Mock()
    client.exceptions.ResourceInUseException = exceptions.ResourceInUseException
    client.start_change_set.side_effect = [
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception(),
        generate_exception()
    ]

    session = Mock()
    session.client.return_value = client

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    with raises(MashEc2UtilsException) as error:
        start_mp_change_set(
            session,
            change_set=[change_set],
            max_rechecks=10,
            rechecks_period=0,
            conflict_wait_period=0
        )
    assert 'Unable to complete successfully the mp change.' \
        in str(error)

    # Mock calls assertions
    session.client.assert_has_calls(
        [
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
            call('marketplace-catalog'),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params)

        ],
    )


def test_start_mp_change_set_ongoing_change_ResInUseExc_not_changeid():

    def generate_resource_in_use_exception():
        error_code = 'ResourceInUseException'
        error_message = "Requested change set has entities locked by change sets" \
                        " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                        " change sets are dgoddlepi9nb3ynwrwlkr3b"
        exc_data = {
            "Error": {
                "Code": error_code,
                "Message": error_message
            },
            "ResponseMetadata": {
                "RequestId": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
                "HTTPStatusCode": 400,
                "HTTPHeaders": {
                    "transfer-encoding": "chunked",
                    "date": "Fri, 01 Jan 2100 00:00:00 GMT",
                    "connection": "close",
                    "server": "AmazonEC2"
                },
                "RetryAttempts": 0
            }
        }

        return exceptions.ResourceInUseException(
            error_response=exc_data,
            operation_name='start_change_set'
        )

    client = Mock()
    client.exceptions.ResourceInUseException = exceptions.ResourceInUseException
    client.start_change_set.side_effect = [
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception(),
        generate_resource_in_use_exception()
    ]

    session = Mock()
    session.client.return_value = client

    change_set = create_add_version_change_doc(
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user'
    )

    with raises(MashEc2UtilsException) as error:
        start_mp_change_set(
            session,
            change_set=[change_set],
            max_rechecks=5,
            rechecks_period=0,
            conflict_wait_period=0
        )
    msg = 'Unable to extract changeset id from aws err response:'
    msg2 = 'dgoddlepi9nb3ynwrwlkr3b'
    assert msg in str(error)
    assert msg2 in str(error)

    # Mock calls asserts
    session.client.assert_has_calls(
        [
            call('marketplace-catalog'),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
        any_order=True
    )


def test_create_restrict_version_change_doc():
    expected = {
        'ChangeType': 'RestrictDeliveryOptions',
        'Entity': {
            'Type': 'AmiProduct@1.0',
            'Identifier': '123456789'
        }
    }
    details = {
        'DeliveryOptionIds': ['987654321']
    }
    expected['Details'] = json.dumps(details)

    actual = create_restrict_version_change_doc('123456789', '987654321')
    assert expected == actual


def test_get_delivery_option_id():
    details = {
        "Versions": [
            {
                "Sources": [
                    {
                        "Image": "ami-123",
                        "Id": "1234"
                    }
                ],
                "DeliveryOptions": [
                    {
                        "Id": "4321",
                        "SourceId": "1234"
                    }
                ]
            }
        ]
    }

    entity = {
        'Details': json.dumps(details)
    }
    session = Mock()
    client = Mock()
    client.describe_entity.return_value = entity
    session.client.return_value = client

    did = get_delivery_option_id(
        session,
        '1234589',
        'ami-123',
    )
    assert did == '4321'

    # Test no image match found
    details['Versions'][0]['Sources'][0]['Image'] = 'ami-321'
    entity['Details'] = json.dumps(details)

    did = get_delivery_option_id(
        session,
        '1234589',
        'ami-123',
    )
    assert did is None


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
            'my_file_name',
            '/my/directory/name'
        )
    ]

    for bucket_name, file_name, directory_name in tests_parameters:
        download_file_from_s3_bucket(
            boto3_session_mock,
            bucket_name,
            file_name,
            directory_name
        )
        boto3_session_mock.client.assert_called_once_with(service_name='s3')
        s3_client_mock.download_file.assert_called_once_with(
            bucket_name,
            file_name,
            os.path.join(directory_name, file_name)
        )
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
            'my_file_name',
            '/my/directory/name'
        )
    ]

    for bucket_name, file_name, directory_name in tests_parameters:
        download_file_from_s3_bucket(
            boto3_session_mock,
            bucket_name,
            file_name,
            directory_name
        )
        boto3_session_mock.client.assert_called_once_with(service_name='s3')
        s3_client_mock.download_file.assert_called_once_with(
            bucket_name,
            file_name,
            os.path.join(directory_name, file_name)
        )
        os_path_exists_mock.assert_called_once_with(directory_name)
        os_makedirs_mock.assert_called_once_with(directory_name)
        os_path_exists_mock.reset_mock()
        boto3_session_mock.reset_mock()
        s3_client_mock.reset_mock()
