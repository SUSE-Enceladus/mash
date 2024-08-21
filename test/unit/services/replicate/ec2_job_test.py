from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashReplicateException
from mash.services.status_levels import FAILED
from mash.services.replicate.ec2_job import EC2ReplicateJob


class TestEC2ReplicateJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'image_description': 'My image',
            'last_service': 'replicate',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now',
            "replicate_source_regions": {
                "us-east-1": {
                    "account": "test-aws",
                    "target_regions": ["us-east-2"]
                }
            }
        }

        self.config = Mock()
        self.job = EC2ReplicateJob(self.job_config, self.config)
        self.job._log_callback = Mock()

        self.job.credentials = {
            "test-aws": {
                'access_key_id': '123456',
                'secret_access_key': '654321'
            }
        }

        self.job.status_msg['cloud_image_name'] = 'My image'
        self.job.status_msg['source_regions'] = {'us-east-1': 'ami-12345'}

    def test_replicate_ec2_missing_key(self):
        del self.job_config['replicate_source_regions']

        with raises(MashReplicateException):
            EC2ReplicateJob(self.job_config, self.config)

    @patch('mash.services.replicate.ec2_job.time')
    @patch.object(EC2ReplicateJob, '_wait_on_image')
    @patch.object(EC2ReplicateJob, '_replicate_to_region')
    def test_replicate(
        self, mock_replicate_to_region,
        mock_wait_on_image, mock_time
    ):
        mock_replicate_to_region.return_value = 'ami-54321'
        mock_wait_on_image.side_effect = Exception('Broken!')

        self.job.run_job()

        self.job._log_callback.info.assert_called_once_with(
            '(test-preparation=False) Replicating source region: us-east-1 to '
            'the following regions: us-east-2.'
        )
        self.job._log_callback.warning.assert_called_once_with(
            'Replicate to us-east-2 region failed: Broken!'
        )

        mock_replicate_to_region.assert_called_once_with(
            self.job.credentials['test-aws'], 'ami-12345',
            'us-east-1', 'us-east-2'
        )
        mock_wait_on_image.assert_called_once_with(
            self.job.credentials['test-aws']['access_key_id'],
            self.job.credentials['test-aws']['secret_access_key'],
            'ami-54321',
            'us-east-2',
            False
        )
        assert self.job.status == FAILED

    @patch.object(EC2ReplicateJob, 'image_exists')
    @patch('mash.services.replicate.ec2_job.get_client')
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
            client,
            'My image'
        )
        client.copy_image.assert_called_once_with(
            Description=self.job.image_description,
            Name='My image',
            SourceImageId='ami-12345',
            SourceRegion='us-east-1',
        )

    @patch.object(EC2ReplicateJob, 'image_exists')
    @patch('mash.services.replicate.ec2_job.get_client')
    def test_replicate_to_region_exists(
            self, mock_get_client, mock_image_exists
    ):
        client = Mock()
        mock_get_client.return_value = client
        mock_image_exists.return_value = True

        result = self.job._replicate_to_region(
            self.job.credentials['test-aws'],
            'ami-12345', 'us-east-1', 'us-east-2'
        )

        assert result is None

    @patch.object(EC2ReplicateJob, 'image_exists')
    @patch('mash.services.replicate.ec2_job.get_client')
    def test_replicate_to_region_exception(
        self, mock_get_client, mock_image_exists
    ):
        client = Mock()
        client.copy_image.side_effect = Exception('Error copying image!')
        mock_get_client.return_value = client
        mock_image_exists.return_value = False

        msg = (
            'There was an error replicating(test_preparation=False) image'
            ' to us-east-2. Error copying image!'
        )
        with raises(MashReplicateException) as e:
            self.job._replicate_to_region(
                self.job.credentials['test-aws'],
                'ami-12345', 'us-east-1', 'us-east-2'
            )

        assert msg == str(e.value)

    @patch('mash.services.replicate.ec2_job.get_client')
    def test_replicate_wait_on_image(self, mock_get_client):
        client = Mock()
        client.describe_images.return_value = {
            'Images': [{'State': 'available'}]
        }
        mock_get_client.return_value = client

        self.job._wait_on_image(
            self.job.credentials['test-aws']['access_key_id'],
            self.job.credentials['test-aws']['secret_access_key'],
            'ami-54321',
            'us-east-2'
        )

        mock_get_client.assert_called_once_with(
            'ec2', '123456', '654321', 'us-east-2'
        )
        client.describe_images.assert_called_once_with(
            Owners=['self'],
            ImageIds=['ami-54321']
        )

    @patch('mash.services.replicate.ec2_job.time')
    @patch('mash.services.replicate.ec2_job.get_client')
    def test_replicate_wait_on_image_exception(
        self, mock_get_client, mock_sleep
    ):
        client = Mock()
        client.describe_images.side_effect = [
            KeyError('Images'),
            {'Images': [{'State': 'pending'}]},
            {'Images': [{'State': 'failed'}]}
        ]
        mock_get_client.return_value = client

        with raises(MashReplicateException):
            self.job._wait_on_image(
                self.job.credentials['test-aws']['access_key_id'],
                self.job.credentials['test-aws']['secret_access_key'],
                'ami-54321',
                'us-east-2'
            )

        with raises(MashReplicateException):
            self.job._wait_on_image(
                self.job.credentials['test-aws']['access_key_id'],
                self.job.credentials['test-aws']['secret_access_key'],
                'ami-54321',
                'us-east-2'
            )

    def test_replicate_image_exists(self):
        images = {'Images': []}
        client = Mock()
        client.describe_images.return_value = images

        result = self.job.image_exists(client, 'image name')

        assert result is False

        images['Images'].append({'Name': 'image name'})
        result = self.job.image_exists(client, 'image name')

        assert result
