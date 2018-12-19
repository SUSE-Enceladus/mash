from pytest import raises
from unittest.mock import Mock, patch

from mash.services.publisher.job import PublisherJob


class TestPublisherJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publisher',
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

    def test_publish(self):
        job = PublisherJob(**self.job_config)
        with raises(NotImplementedError):
            job._publish()

    @patch.object(PublisherJob, '_publish')
    def test_publish_image(self, mock_publish):
        job = PublisherJob(**self.job_config)
        job.log_callback = Mock()
        job.publish_image()

        mock_publish.assert_called_once_with()
