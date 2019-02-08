from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashTestingException
from mash.services.testing.testing_job import TestingJob


class TestTestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'ec2',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {'us-east-1': 'test-aws'},
            'tests': ['test_stuff'],
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = TestingJob(**self.job_config)

        assert job.id == '1'
        assert job.cloud == 'ec2'
        assert job.tests == ['test_stuff']
        assert job.utctime == 'now'

    def test_add_cloud_creds(self):
        job = TestingJob(**self.job_config)
        with raises(NotImplementedError):
            job._add_cloud_creds(
                {'creds': 'dict'},
                {}
            )

    def test_source_regions(self):
        job = TestingJob(**self.job_config)
        job.source_regions = {'west': 'ami-123'}
        assert job.source_regions['west'] == 'ami-123'

    @patch.object(TestingJob, '_run_tests')
    def test_test_image(self, mock_run_tests):
        job = TestingJob(**self.job_config)
        job.log_callback = Mock()
        job.process_job()

        job.log_callback.assert_called_once_with(
            'Pass[1]: Running IPA tests against image.',
            {'job_id': '1'},
            True
        )

    def test_invalid_test_regions(self):
        self.job_config['test_regions'] = {'us-east-1': None}
        msg = 'Invalid test_regions format. ' \
            'Must be a dict format of {region:account}.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg
