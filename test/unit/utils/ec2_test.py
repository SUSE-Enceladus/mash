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

from pytest import raises
from unittest.mock import Mock, patch
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
import botocore
from botocore.stub import Stubber, ANY


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


def test_start_mp_change_set():
    client = Mock()
    client.start_change_set.return_value = {
        'ChangeSetId': '123'
    }

    response = start_mp_change_set(
        client,
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


def test_start_mp_change_set_ongoing_change_ResourceInUseException():
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ResourceInUseException'
    error_message = "Requested change set has entities locked by change sets" \
                    " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                    " change sets: dgoddlepi9nb3ynwrwlkr3be4."

    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    describe_response = {
        'Status': 'APPLYING'
    }
    # First check will still be applying
    stubber.add_response(
        'describe_change_set',
        describe_response,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    describe_response2 = {
        'Status': 'SUCCEEDED'
    }
    # Second check succeeded
    stubber.add_response(
        'describe_change_set',
        describe_response2,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    start_response1 = {
        'ChangeSetId': 'myChangeSetId',
        'ChangeSetArn': 'myChangeSetArn'
    }
    # successful response for start_change_set
    stubber.add_response(
        'start_change_set',
        start_response1,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSet': ANY
        }
    )
    stubber.activate()

    with stubber:
        start_mp_change_set(
            client,
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
    stubber.deactivate()


def test_start_mp_change_set_ongoing_change_GenericException():
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ServiceQuotaExceededException'
    error_message = "Quota is exceeded"

    # different exception for start_change_set x3
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    stubber.activate()

    with stubber:
        with raises(Exception) as error:
            start_mp_change_set(
                client,
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
                max_rechecks=20,
                rechecks_period=0
            )
            assert 'ServiceQuotaExceededException' in str(error)
        stubber.deactivate()


def test_start_mp_change_set_ongoing_change_ResourceInUseException_3times():
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ResourceInUseException'
    error_message = "Requested change set has entities locked by change sets" \
                    " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                    " change sets: dgoddlepi9nb3ynwrwlkr3be4."

    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    describe_response = {
        'Status': 'SUCCEEDED'
    }
    # check succeeds, blocking changeset finished
    stubber.add_response(
        'describe_change_set',
        describe_response,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    # another time, ResourceInUseException
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    describe_response = {
        'Status': 'SUCCEEDED'
    }
    # Second check succeeded
    stubber.add_response(
        'describe_change_set',
        describe_response,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    # another time, ResourceInUseException
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    describe_response = {
        'Status': 'SUCCEEDED'
    }
    # Second check succeeded
    stubber.add_response(
        'describe_change_set',
        describe_response,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    stubber.activate()

    with stubber:
        with raises(MashEc2UtilsException) as error:
            start_mp_change_set(
                client,
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
                max_rechecks=20,
                rechecks_period=0
            )
            msg = 'Unable to complete successfully the mp change for ami-123'
            assert msg in str(error)
        stubber.deactivate()


def test_start_mp_change_set_ongoing_change_ResInUseExc_genericExc():
    """Describe generates a generic exception"""
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ResourceInUseException'
    error_message = "Requested change set has entities locked by change sets" \
                    " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                    " change sets: dgoddlepi9nb3ynwrwlkr3be4."
    # ResourceInUseException
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )

    # Different exception in describe_change_set
    error_code2 = 'AccessDeniedException'
    error_message2 = 'You are not authorized to perform this request'
    stubber.add_client_error(
        'describe_change_set',
        error_code2,
        error_message2
    )
    stubber.activate()

    with stubber:
        with raises(Exception):
            start_mp_change_set(
                client,
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
                max_rechecks=20,
                rechecks_period=0
            )
        stubber.deactivate()


def test_start_mp_change_set_ongoing_change_ResInUseExc_waitTimeout():
    """Describe generates a generic exception"""
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ResourceInUseException'
    error_message = "Requested change set has entities locked by change sets" \
                    " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                    " change sets: dgoddlepi9nb3ynwrwlkr3be4."
    # ResourceInUseException
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )

    # Ongoing
    describe_response = {
        'Status': 'PENDING'
    }
    # Second check succeeded
    stubber.add_response(
        'describe_change_set',
        describe_response,
        {
            'Catalog': 'AWSMarketplace',
            'ChangeSetId': 'dgoddlepi9nb3ynwrwlkr3be4'
        }
    )
    stubber.activate()

    with stubber:
        with raises(MashEc2UtilsException) as error:
            start_mp_change_set(
                client,
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
                max_rechecks=1,
                rechecks_period=0
            )
            msg = 'Timed out waiting for conflicting mp changeset'
            msg += ' dgoddlepi9nb3ynwrwlkr3be4 to finish'
            assert msg in str(error)
        stubber.deactivate()


def test_start_mp_change_set_ongoing_change_ResInUseExc_not_changeid():
    """Describe generates a generic exception"""
    session = botocore.session.get_session()
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = session.create_client(
        'marketplace-catalog',
        'us-east-1',
        config=config
    )

    stubber = Stubber(client)
    error_code = 'ResourceInUseException'
    error_message = "Requested change set has entities locked by change sets" \
                    " - entity: '6066beac-a43b-4ad0-b5fe-f503025e4747' " \
                    " change sets are dgoddlepi9nb3ynwrwlkr3be4"
    # ResourceInUseException
    stubber.add_client_error(
        'start_change_set',
        error_code,
        error_message
    )
    stubber.activate()

    with stubber:
        with raises(MashEc2UtilsException) as error:
            start_mp_change_set(
                client,
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
                max_rechecks=1,
                rechecks_period=0
            )
            msg = 'Unable to extract changeset id from aws err response:'
            msg2 = 'dgoddlepi9nb3ynwrwlkr3be4'
            assert msg in str(error)
            assert msg2 in str(error)
        stubber.deactivate()
