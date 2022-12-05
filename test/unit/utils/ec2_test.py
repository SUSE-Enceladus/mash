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

from pytest import raises
from unittest.mock import Mock, patch, call
from mash.utils.ec2 import (
    get_client,
    get_vpc_id_from_subnet,
    cleanup_ec2_image,
    cleanup_all_ec2_images,
    get_image,
    image_exists,
    start_mp_change_set
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

    mock_describe_images.return_value = [image]
    result = get_image(client, 'image name 123')
    assert result == image


@patch('mash.utils.ec2.get_image')
def test_image_exists(mock_get_image):
    client = Mock()
    image = {'Name': 'image name 123'}
    mock_get_image.return_value = image

    assert image_exists(client, 'image name 123')
    assert not image_exists(client, 'image name 321')


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set(mock_get_client):
    client = Mock()
    client.start_change_set.return_value = {
        'ChangeSetId': '123'
    }
    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'
    response = start_mp_change_set(
        region,
        access_key,
        secret_access_key,
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

    assert response['ChangeSetId'] == '123'
    client.start_change_set.assert_called_once_with(**start_changeset_params)
    mock_get_client.assert_called_once_with(*get_client_args)


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_ResourceInUseException(
    mock_get_client
):

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
    client.describe_change_set.side_effect = [
        {
            'Status': 'APPLYING'
        },
        {
            'Status': 'FINISHED'
        }
    ]
    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    response = start_mp_change_set(
        region,
        access_key,
        secret_access_key,
        entity_id='123',
        version_title='New image',
        ami_id='ami-123',
        access_role_arn='arn',
        release_notes='Release Notes',
        os_name='OTHERLINUX',
        os_version='15.3',
        usage_instructions='Login with SSH...',
        recommended_instance_type='t3.medium',
        ssh_user='ec2-user',
        max_rechecks=10,
        rechecks_period=0
    )
    assert response.get('ChangeSetId') == 'myChangeSetId'
    # Mock calls assertions
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
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
    client.describe_change_set.assert_has_calls(
        [
            call(**describe_changeset_params),
            call(**describe_changeset_params)
        ],
        any_order=True
    )


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_GenericException(
    mock_get_client
):

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
    ]

    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    with raises(Exception) as error:
        start_mp_change_set(
            region,
            access_key,
            secret_access_key,
            entity_id='123',
            version_title='New image',
            ami_id='ami-123',
            access_role_arn='arn',
            release_notes='Release Notes',
            os_name='OTHERLINUX',
            os_version='15.3',
            usage_instructions='Login with SSH...',
            recommended_instance_type='t3.medium',
            ssh_user='ec2-user',
            max_rechecks=10,
            rechecks_period=0
        )
    assert 'AccessDeniedException' in str(error)

    # Mock calls assertions
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
        ],
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params)
        ],
    )


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_ResourceInUseException_3times(
    mock_get_client
):

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
        generate_exception()
    ]

    client.describe_change_set.side_effect = [
        {
            'Status': 'FINISHED'
        },
        {
            'Status': 'FINISHED'
        },
        {
            'Status': 'FINISHED'
        }
    ]

    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    with raises(MashEc2UtilsException) as error:
        start_mp_change_set(
            region,
            access_key,
            secret_access_key,
            entity_id='123',
            version_title='New image',
            ami_id='ami-123',
            access_role_arn='arn',
            release_notes='Release Notes',
            os_name='OTHERLINUX',
            os_version='15.3',
            usage_instructions='Login with SSH...',
            recommended_instance_type='t3.medium',
            ssh_user='ec2-user',
            max_rechecks=10,
            rechecks_period=0
        )
    assert 'Unable to complete successfully the mp change for ami-123.' \
        in str(error)

    # Mock calls assertions
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
            call(**start_changeset_params),
            call(**start_changeset_params)

        ],
    )
    client.describe_change_set.assert_has_calls(
        [
            call(**describe_changeset_params),
            call(**describe_changeset_params),
            call(**describe_changeset_params)
        ],
        any_order=True
    )


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_ResInUseExc_genericExc(
    mock_get_client
):
    """Describe generates a generic exception"""

    def generate_resource_in_use_exception():
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

    def generate_access_denied_exception():
        error_code = 'AccessDeniedException'
        error_message = "AccessDenied"
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
            operation_name='describe_change_set'
        )

    client = Mock()
    client.exceptions.ResourceInUseException = exceptions.ResourceInUseException
    client.start_change_set.side_effect = [
        generate_resource_in_use_exception()
    ]

    client.exceptions.AccessDeniedException = exceptions.AccessDeniedException
    client.describe_change_set.side_effect = [
        generate_access_denied_exception()
    ]

    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    with raises(Exception) as error:
        start_mp_change_set(
            region,
            access_key,
            secret_access_key,
            entity_id='123',
            version_title='New image',
            ami_id='ami-123',
            access_role_arn='arn',
            release_notes='Release Notes',
            os_name='OTHERLINUX',
            os_version='15.3',
            usage_instructions='Login with SSH...',
            recommended_instance_type='t3.medium',
            ssh_user='ec2-user',
            max_rechecks=10,
            rechecks_period=0
        )
    assert 'AccessDenied' in str(error)

    # mock call asserts
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
            call(*get_client_args),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
    )
    client.describe_change_set.assert_has_calls(
        [
            call(**describe_changeset_params),
        ],
        any_order=True
    )


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_ResInUseExc_waitTimeout(
    mock_get_client
):

    def generate_resource_in_use_exception():
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
        generate_resource_in_use_exception()
    ]

    client.describe_change_set.side_effect = [
        {
            'Status': 'PENDING'
        },
        {
            'Status': 'PENDING'
        },
        {
            'Status': 'PENDING'
        },
        {
            'Status': 'PENDING'
        },
        {
            'Status': 'PENDING'
        }
    ]

    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    with raises(MashEc2UtilsException) as error:
        start_mp_change_set(
            region,
            access_key,
            secret_access_key,
            entity_id='123',
            version_title='New image',
            ami_id='ami-123',
            access_role_arn='arn',
            release_notes='Release Notes',
            os_name='OTHERLINUX',
            os_version='15.3',
            usage_instructions='Login with SSH...',
            recommended_instance_type='t3.medium',
            ssh_user='ec2-user',
            max_rechecks=5,
            rechecks_period=0
        )
    msg = 'Timed out waiting for conflicting mp changeset dgoddlepi9nb3ynwrwlkr3be4'
    assert msg in str(error)

    # Mock calls asserts
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args),
            call(*get_client_args)
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
        any_order=True
    )
    client.describe_change_set.assert_has_calls(
        [
            call(**describe_changeset_params),
            call(**describe_changeset_params),
            call(**describe_changeset_params),
            call(**describe_changeset_params),
            call(**describe_changeset_params),
        ],
        any_order=True
    )


@patch('mash.utils.ec2.get_client')
def test_start_mp_change_set_ongoing_change_ResInUseExc_not_changeid(
    mock_get_client
):

    def generate_resource_in_use_exception():
        error_code = 'ResourceInUseException'
        error_message = "Requested change set has entities locked by change sets" \
                        " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                        " change sets are dgoddlepi9nb3ynwrwlkr3be4."
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
        generate_resource_in_use_exception()
    ]

    mock_get_client.return_value = client

    region = 'us-east-1'
    access_key = '123456'
    secret_access_key = '654321'

    with raises(MashEc2UtilsException) as error:
        start_mp_change_set(
            region,
            access_key,
            secret_access_key,
            entity_id='123',
            version_title='New image',
            ami_id='ami-123',
            access_role_arn='arn',
            release_notes='Release Notes',
            os_name='OTHERLINUX',
            os_version='15.3',
            usage_instructions='Login with SSH...',
            recommended_instance_type='t3.medium',
            ssh_user='ec2-user',
            max_rechecks=5,
            rechecks_period=0
        )
    msg = 'Unable to extract changeset id from aws err response:'
    msg2 = 'dgoddlepi9nb3ynwrwlkr3be4'
    assert msg in str(error)
    assert msg2 in str(error)

    # Mock calls asserts
    mock_get_client.assert_has_calls(
        [
            call(*get_client_args),
        ],
        any_order=True
    )
    client.start_change_set.assert_has_calls(
        [
            call(**start_changeset_params),
        ],
        any_order=True
    )
    client.describe_change_set.assert_not_called()
