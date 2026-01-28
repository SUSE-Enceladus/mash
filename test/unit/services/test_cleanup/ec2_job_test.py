import pytest

from unittest.mock import call, Mock, patch

from mash.services.test_cleanup.ec2_job import EC2TestCleanupJob
from mash.mash_exceptions import MashTestCleanupException


class TestEC2TestJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_cleanup_regions': {
                'us-east-1': {
                    'account': 'test-aws',
                    'partition': 'aws',
                    'target_regions': ['us-east-2', 'eu-central-1']
                }
            },
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cleanup_images': True
        }
        self.config = Mock()

    def test_test_cleanup_ec2_missing_key(self):
        del self.job_config['test_cleanup_regions']

        with pytest.raises(MashTestCleanupException):
            EC2TestCleanupJob(self.job_config, self.config)

    @patch('mash.services.test_cleanup.ec2_job.cleanup_ec2_image')
    def test_test_run_test(
        self,
        mock_cleanup_image
    ):

        job = EC2TestCleanupJob(self.job_config, self.config)
        job._log_callback = Mock()

        job.credentials = {
            'test-aws': {
                'access_key_id': '123',
                'secret_access_key': '321'
            }
        }
        job.status_msg['test_replicated_regions'] = {
            'us-east-2': 'ami-111111',
            'eu-central-1': 'ami-222222',

        }
        job.run_job()

        mock_cleanup_image.assert_has_calls([
            call(
                '123',
                '321',
                job._log_callback,
                'us-east-2',
                image_id='ami-111111'
            ),
            call(
                '123',
                '321',
                job._log_callback,
                'eu-central-1',
                image_id='ami-222222'
            )
        ])
        job._log_callback.warning.reset_mock()
