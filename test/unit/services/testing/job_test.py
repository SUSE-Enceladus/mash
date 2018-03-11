from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashTestingException
from mash.services.testing.job import TestingJob


class TestTestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'ec2',
            'test_regions': {'us-east-1': 'test-aws'},
            'tests': 'test_stuff',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = TestingJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'ec2'
        assert job.tests == ['test_stuff']
        assert job.utctime == 'now'

    def test_job_get_metadata(self):
        job = TestingJob(**self.job_config)
        metadata = job.get_metadata()
        assert metadata == {'job_id': '1'}

    def test_run_tests(self):
        job = TestingJob(**self.job_config)
        with raises(NotImplementedError):
            job._run_tests()

    def test_set_log_callback(self):
        job = TestingJob(**self.job_config)
        callback = Mock()
        job.set_log_callback(callback)

        assert job.log_callback == callback

    @patch.object(TestingJob, '_run_tests')
    def test_test_image(self, mock_run_tests):
        job = TestingJob(**self.job_config)
        job.log_callback = Mock()
        job.test_image()

        job.log_callback.assert_called_once_with(
            'Pass[1]: Running IPA tests against image.',
            {'job_id': '1'},
            True
        )

    def test_invalid_distro(self):
        self.job_config['distro'] = 'Fake'
        msg = 'Distro: Fake not supported.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_provider(self):
        self.job_config['provider'] = 'Fake'
        msg = 'Provider: Fake not supported.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_tests(self):
        self.job_config['tests'] = ''
        msg = 'Must provide at least one test.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

        self.job_config['tests'] = ['test_stuff']
        msg = 'Invalid tests format, must be a comma seperated list.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_test_regions(self):
        self.job_config['test_regions'] = {'us-east-1': None}
        msg = 'Invalid test_regions format. ' \
            'Must be a dict format of {region:account}.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_timestamp(self):
        self.job_config['utctime'] = 'never'
        msg = 'Invalid utctime format: Unknown string format'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg
