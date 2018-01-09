from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher.utils import (
    copy_image_to_region, ec2_image_replicate, image_exists,
    get_client_from_session, get_session, get_regions
)


@patch('mash.services.publisher.utils.get_client_from_session')
@patch('mash.services.publisher.utils.get_session')
@patch('mash.services.publisher.utils.image_exists')
def test_copy_image_to_region(
    mock_image_exists, mock_get_session, mock_get_client_from_session
):
    waiter = Mock()
    session = Mock()

    client = Mock()
    client.copy_image.return_value = {'ImageId': 'ami-12345'}
    client.get_waiter.return_value = waiter

    mock_image_exists.return_value = False
    mock_get_session.return_value = session
    mock_get_client_from_session.return_value = client

    value = copy_image_to_region(
        None, 'Test image description', 'ami-54321', 'Test image name',
        'us-west-1', None, 'us-east-1'
    )

    assert value == 'us-west-1'

    client.copy_image.assert_called_once_with(
        Description='Test image description',
        Name='Test image name',
        SourceImageId='ami-54321',
        SourceRegion='us-east-1',
    )
    client.get_waiter.assert_called_once_with('image_available')
    waiter.wait.assert_called_once_with(
        ImageIds=['ami-12345'],
        Filters=[{'Name': 'state', 'Values': ['available']}],
        WaiterConfig={
            'Delay': 15,
            'MaxAttempts': 80
        }
    )

    client.copy_image.side_effect = Exception('Error copying image.')

    msg = 'There was an error replicating image to us-west-1. ' \
          'Error copying image.'
    with raises(MashPublisherException) as e:
        copy_image_to_region(
            None, 'Test image description', 'ami-54321', 'Test image name',
            'us-west-1', None, 'us-east-1'
        )

    assert msg == str(e.value)


@patch('mash.services.publisher.utils.copy_image_to_region')
def test_ec2_image_replicate(mock_copy_image_to_region):
    mock_copy_image_to_region.return_value = 'us-west-1'

    ec2_image_replicate(
        None, 'Test image description', 'ami-54321', 'Test image name',
        None, ['us-west-1', 'us-west-2'], 'us-east-1'
    )


@patch('mash.services.publisher.utils.replicate')
@patch('mash.services.publisher.utils.asyncio.new_event_loop')
def test_ec2_image_replicate_loop_close(mock_asyncio, mock_replicate):
    loop = Mock()
    loop.is_closed = False
    mock_asyncio.return_value = loop

    ec2_image_replicate(
        None, 'Test image description', 'ami-54321', 'Test image name',
        None, ['us-west-1', 'us-west-2'], 'us-east-1'
    )
    loop.close.assert_called_once_with()


@patch('mash.services.publisher.utils.copy_image_to_region')
def test_ec2_image_replicate_exception(mock_copy_image_to_region):
    mock_copy_image_to_region.side_effect = MashPublisherException(
        'Error copying image.'
    )

    msg = 'Error copying image.'
    with raises(MashPublisherException) as e:
        ec2_image_replicate(
            None, 'Test image description', 'ami-54321', 'Test image name',
            None, ['us-west-1', 'us-west-2'], 'us-east-1'
        )

    assert msg == str(e.value)


def test_image_exists():
    client = Mock()
    client.describe_images.return_value = {
        'Images': [{'Name': 'Test image name'}]
    }

    result = image_exists(client, 'Test image name')
    assert result

    client.describe_images.return_value = {'Images': []}
    result = image_exists(client, 'Test image name')
    assert not result


def test_get_client_from_session():
    client = Mock()
    session = Mock()

    session.client.return_value = client
    result = get_client_from_session(session, 'sts')

    assert result == client
    session.client.assert_called_once_with('sts')


@patch('mash.services.publisher.utils.boto3')
def test_get_session(mock_boto3):
    session = Mock()

    mock_boto3.session.Session.return_value = session
    result = get_session('123456', 'abc123')

    assert session == result
    mock_boto3.session.Session.assert_called_once_with(
        aws_access_key_id='123456',
        aws_secret_access_key='abc123',
        region_name=None,
    )


@patch('mash.services.publisher.utils.get_client_from_session')
@patch('mash.services.publisher.utils.get_session')
def test_get_regions(mock_get_session, mock_get_client_from_session):
    session = Mock()
    client = Mock()
    client.get_caller_identity.return_value = {
        'Arn': 'arn:aws:iam::123456789012:user/Jarvis'
    }

    mock_get_session.return_value = session
    mock_get_client_from_session.return_value = client

    get_regions('123456', 'abc123', 'us-west-1')

    session.get_available_regions.assert_called_once_with(
        'ec2', partition_name='aws'
    )
