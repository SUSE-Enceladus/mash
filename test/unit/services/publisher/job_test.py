from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher.job import PublisherJob


class TestPublisherJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'ec2',
            'publish_regions': [
                {
                    'account': 'test-aws',
                    'target_regions': ['us-east-2']
                }
            ],
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = PublisherJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'ec2'
        assert job.utctime == 'now'

    def test_job_get_metadata(self):
        job = PublisherJob(**self.job_config)
        metadata = job.get_metadata()
        assert metadata == {'job_id': '1'}

    def test_publish(self):
        job = PublisherJob(**self.job_config)
        with raises(NotImplementedError):
            job._publish()

    def test_send_log(self):
        callback = Mock()

        job = PublisherJob(**self.job_config)
        job.log_callback = callback
        job.iteration_count = 0

        job.send_log('Starting publish.')

        callback.assert_called_once_with(
            'Pass[0]: Starting publish.',
            {'job_id': '1'},
            True
        )

    def test_set_log_callback(self):
        test = Mock()

        job = PublisherJob(**self.job_config)
        job.set_log_callback(test.method)

        assert job.log_callback == test.method

    @patch.object(PublisherJob, '_publish')
    def test_publish_image(self, mock_publish):
        job = PublisherJob(**self.job_config)
        job.log_callback = Mock()
        job.publish_image('localhost')

        mock_publish.assert_called_once_with()

    def test_invalid_provider(self):
        self.job_config['provider'] = 'Provider'
        msg = 'Provider: Provider not supported.'
        with raises(MashPublisherException) as e:
            PublisherJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_publish_regions(self):
        msg = 'Invalid publish_regions format. ' \
            'Must be a list of dictionaries with account' \
            ' and target_regions keys.'
        self.job_config['publish_regions'] = [{
            'account': 'test-aws',
            'target_regions': None
        }]
        with raises(MashPublisherException) as e:
            PublisherJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_timestamp(self):
        self.job_config['utctime'] = 'never'
        msg = 'Invalid utctime format: Unknown string format'
        with raises(MashPublisherException) as e:
            PublisherJob(**self.job_config)

        assert str(e.value) == msg
