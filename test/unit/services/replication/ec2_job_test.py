from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashReplicationException
from mash.services.credentials.amazon import CredentialsAmazon
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.job import ReplicationJob


class TestEC2ReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'image_description': 'My image',
            'provider': 'ec2',
            'utctime': 'now',
            "source_regions": {
                "us-east-1": {
                    "account": "test-aws",
                    "target_regions": ["us-east-2"]
                }
            }
        }
        self.job = EC2ReplicationJob(**self.job_config)
        self.job.update_source_regions({'us-east-1': 'ami-12345'})

        args = {
            'access_key_id': '123456',
            'secret_access_key': '654321',
            'ssh_key_name': 'my-key',
            'ssh_private_key': 'my-key.pem'
        }
        self.job.credentials = {
            "test-aws": CredentialsAmazon(custom_args=args)
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

        credential = Mock()
        credential.access_key_id = '123456'
        credential.secret_access_key = '654321'

        self.job.cloud_image_name = 'My image'

        self.job._replicate_to_region(
            credential, 'ami-12345', 'us-east-1', 'us-east-2'
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

        credential = Mock()
        credential.access_key_id = '123456'
        credential.secret_access_key = '654321'

        msg = 'There was an error replicating image to us-east-2. ' \
            'Error copying image!'
        with raises(MashReplicationException) as e:
            self.job._replicate_to_region(
                credential, 'ami-12345', 'us-east-1', 'us-east-2'
            )

        assert msg == str(e.value)

    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_wait_on_image(self, mock_get_client):
        client = Mock()
        waiter = Mock()
        client.get_waiter.return_value = waiter
        mock_get_client.return_value = client

        credential = Mock()
        credential.access_key_id = '123456'
        credential.secret_access_key = '654321'

        self.job._wait_on_image(credential, 'ami-54321', 'us-east-2')

        mock_get_client.assert_called_once_with(
            'ec2', '123456', '654321', 'us-east-2'
        )
        client.get_waiter.assert_called_once_with('image_available')
        waiter.wait.assert_called_once_with(
            ImageIds=['ami-54321'],
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )

    @patch('mash.services.replication.ec2_job.get_client')
    def test_replicate_wait_on_image_exception(self, mock_get_client):
        client = Mock()
        client.get_waiter.side_effect = Exception('Error copying image!')
        mock_get_client.return_value = client

        credential = Mock()
        credential.access_key_id = '123456'
        credential.secret_access_key = '654321'

        msg = 'There was an error replicating image to us-east-2. ' \
            'Error copying image!'
        with raises(MashReplicationException) as e:
            self.job._wait_on_image(credential, 'awi-54321', 'us-east-2')

        assert msg == str(e.value)

    def test_replicate_get_source_regions_result(self):
        self.job.source_region_results = {
            'us-east-2': {
                'image_id': 'ami-54321',
                'account': Mock()
            }
        }

        result = self.job.get_source_regions_result()

        assert result['us-east-2'] == 'ami-54321'

    def test_replicate_image_exists(self):
        images = {'Images': []}
        client = Mock()
        client.describe_images.return_value = images

        result = self.job.image_exists(client, 'image name')

        assert result is False

        images['Images'].append({'Name': 'image name'})
        result = self.job.image_exists(client, 'image name')

        assert result

    def test_replicate_validate_source_regions_exceptions(self):
        source_regions = {'us-east-2': {}}

        msg = 'Source region us-east-2 missing account name.'
        with raises(MashReplicationException) as error:
            self.job.validate_source_regions(source_regions)
        assert msg == str(error.value)

        source_regions = {'us-east-2': {'account': 'test-aws'}}

        msg = 'Source region us-east-2 missing target regions.'
        with raises(MashReplicationException) as error:
            self.job.validate_source_regions(source_regions)
        assert msg == str(error.value)
