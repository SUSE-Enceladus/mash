from pytest import raises
from unittest.mock import Mock, patch, call

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
            'test_preparation': True,
            "replicate_source_regions": {
                "us-east-1": {
                    "account": "test-aws",
                    "target_regions": ["us-east-2", 'us-east-3']
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

        self.job._log_callback.info.assert_has_calls([
            call(
                '(test-preparation=True) Replicating source region: us-east-1 to '
                'the following regions: us-east-2, us-east-3.'
            ),
            call('Replicated image to us-east-2 region: ami-54321.'),
            call('Replicated image to us-east-3 region: ami-54321.')
        ])
        self.job._log_callback.warning.assert_has_calls([
            call('Replicate to us-east-2 region failed: Broken!'),
            call('Replicate to us-east-3 region failed: Broken!')
        ])

        mock_replicate_to_region.assert_has_calls([
            call(
                self.job.credentials['test-aws'],
                'ami-12345',
                'us-east-1',
                'us-east-2'
            ),
            call(
                self.job.credentials['test-aws'],
                'ami-12345',
                'us-east-1',
                'us-east-3'
            )
        ])
        mock_wait_on_image.assert_has_calls([
            call(
                self.job.credentials['test-aws']['access_key_id'],
                self.job.credentials['test-aws']['secret_access_key'],
                'ami-54321',
                'us-east-2',
                True
            ),
            call(
                self.job.credentials['test-aws']['access_key_id'],
                self.job.credentials['test-aws']['secret_access_key'],
                'ami-54321',
                'us-east-3',
                True
            )
        ])
        assert self.job.status == FAILED
        assert 'us-east-2' in self.job.status_msg['test_replicated_regions']
        assert 'us-east-3' in self.job.status_msg['test_replicated_regions']
