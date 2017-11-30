from pytest import raises

from mash.mash_exceptions import MashTestingException
from mash.services.testing.testing_job import TestingJob


class TestTestingJob(object):
    def test_valid_job(self):
        job_config = {
            'account': 'account',
            'job_id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }
        job = TestingJob(**job_config)

        assert job.account == 'account'
        assert job.job_id == '1'
        assert job.provider == 'EC2'
        assert job.tests == ['test_stuff']
        assert job.utctime == 'now'

    def test_invalid_provider(self):
        job_config = {
            'account': 'account',
            'job_id': '1',
            'provider': 'Fake',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        msg = 'Provider: Fake not supported.'
        with raises(MashTestingException) as e:
            TestingJob(**job_config)

        assert str(e.value) == msg

    def test_invalid_tests(self):
        job_config = {
            'account': 'account',
            'job_id': '1',
            'provider': 'EC2',
            'tests': '',
            'utctime': 'now'
        }

        msg = 'Must provide at least one test.'
        with raises(MashTestingException) as e:
            TestingJob(**job_config)

        assert str(e.value) == msg

        job_config['tests'] = ['test_stuff']
        msg = 'Invalid tests format, must be a comma seperated list.'
        with raises(MashTestingException) as e:
            TestingJob(**job_config)

        assert str(e.value) == msg

    def test_invalid_timestamp(self):
        job_config = {
            'account': 'account',
            'job_id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'never'
        }

        msg = 'Invalid utctime format: Unknown string format'
        with raises(MashTestingException) as e:
            TestingJob(**job_config)

        assert str(e.value) == msg
