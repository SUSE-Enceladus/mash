from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashReplicationException
from mash.services.status_levels import FAILED
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.replication_job import ReplicationJob


class TestEC2ReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'image_description': 'My image',
            'last_service': 'replication',
            'cloud': 'ec2',
            'utctime': 'now',
            "replication_source_regions": {
                "us-east-1": {
                    "account": "test-aws",
                    "target_regions": ["us-east-2"]
                }
            }
        }
        self.job = EC2ReplicationJob(**self.job_config)

        self.job.credentials = {
            "test-aws": {
                'access_key_id': '123456',
                'secret_access_key': '654321'
            }
        }

    @patch('mash.services.replication.ec2_job.time')
    @patch.object(EC2ReplicationJob, '_wait_on_image')
    @patch.object(EC2ReplicationJob, '_replicate_to_region')
    @patch.object(ReplicationJob, 'send_log')
    def test_replicate(
        self, mock_send_log, mock_replicate_to_region,
        mock_wait_on_image, mock_time
    ):
        mock_replicate_to_region.return_value = 'ami-54321'

        self.job.source_regions = {'us-east-1': 'ami-12345'}
        self.job._replicate()

        mock_send_log.assert_called_once_with(
            'Replicating source region: us-east-1 to the following regions: '
            'us-east-2.'
        )

        mock_replicate_to_region.assert_called_once_with(
            self.job.credentials['test-aws'], 'ami-12345',
            'us-east-1', 'us-east-2'
        )
        mock_wait_on_image.assert_called_once_with(
            self.job.credentials['test-aws'], 'ami-54321', 'us-east-2'
        )

    @patch.object(EC2ReplicationJob, 'image_exists')
    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_to_region(
        self, mock_get_client, mock_image_exists
    ):
        client = Mock()
        client.copy_image.return_value = {'ImageId': 'ami-12345'}
        mock_get_client.return_value = client
        mock_image_exists.return_value = False

        self.job.cloud_image_name = 'My image'

        self.job._replicate_to_region(
            self.job.credentials['test-aws'],
            'ami-12345', 'us-east-1', 'us-east-2'
        )

        mock_get_client.assert_called_once_with(
            'ec2', '123456', '654321', 'us-east-2'
        )
        mock_image_exists.assert_called_once_with(
            client, self.job.cloud_image_name
        )
        client.copy_image.assert_called_once_with(
            Description=self.job.image_description,
            Name=self.job.cloud_image_name,
            SourceImageId='ami-12345',
            SourceRegion='us-east-1',
        )

    @patch.object(EC2ReplicationJob, 'image_exists')
    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_to_region_exception(
        self, mock_get_client, mock_image_exists
    ):
        client = Mock()
        client.copy_image.side_effect = Exception('Error copying image!')
        mock_get_client.return_value = client
        mock_image_exists.return_value = False

        msg = 'There was an error replicating image to us-east-2. ' \
            'Error copying image!'
        with raises(MashReplicationException) as e:
            self.job._replicate_to_region(
                self.job.credentials['test-aws'],
                'ami-12345', 'us-east-1', 'us-east-2'
            )

        assert msg == str(e.value)

    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_wait_on_image(self, mock_get_client):
        client = Mock()
        waiter = Mock()
        client.get_waiter.return_value = waiter
        mock_get_client.return_value = client

        self.job._wait_on_image(
            self.job.credentials['test-aws'], 'ami-54321', 'us-east-2'
        )

        mock_get_client.assert_called_once_with(
            'ec2', '123456', '654321', 'us-east-2'
        )
        client.get_waiter.assert_called_once_with('image_available')
        waiter.wait.assert_called_once_with(
            ImageIds=['ami-54321'],
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )

    @patch.object(ReplicationJob, 'send_log')
    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_wait_on_image_exception(
        self, mock_get_client, mock_send_log
    ):
        client = Mock()
        client.get_waiter.side_effect = Exception('Error copying image!')
        mock_get_client.return_value = client

        self.job._wait_on_image(
            self.job.credentials['test-aws'], 'awi-54321', 'us-east-2'
        )

        mock_send_log.assert_called_once_with(
            'There was an error replicating image to us-east-2. '
            'Error copying image!',
            False
        )
        assert self.job.status == FAILED

    def test_replicate_image_exists(self):
        images = {'Images': []}
        client = Mock()
        client.describe_images.return_value = images

        result = self.job.image_exists(client, 'image name')

        assert result is False

        images['Images'].append({'Name': 'image name'})
        result = self.job.image_exists(client, 'image name')

        assert result
