from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher.ec2_job import EC2PublisherJob
from mash.services.publisher.job import PublisherJob


class TestEC2PublisherJob(object):
    def setup(self):
        self.job_config = {
            'allow_copy': False,
            'id': '1',
            'provider': 'ec2',
            'publish_regions': [
                {
                    'account': 'test-aws',
                    'target_regions': ['us-east-2']
                }
            ],
            'share_with': 'all',
            'utctime': 'now'
        }

        self.job = EC2PublisherJob(**self.job_config)
        self.job.credentials = {
            'test-aws': {
                'access_key_id': '123456',
                'secret_access_key': '654321',
                'ssh_key_name': 'key-123',
                'ssh_private_key': 'key123'
            }
        }

    @patch('mash.services.publisher.ec2_job.EC2PublishImage')
    def test_publish(self, mock_ec2_publish_image):
        publisher = Mock()
        mock_ec2_publish_image.return_value = publisher

        self.job.source_regions = {'us-east-2': 'ami-123456'}
        self.job._publish()

        mock_ec2_publish_image.assert_called_once_with(
            access_key='123456', allow_copy=False,
            secret_key='654321', verbose=False, visibility='all'
        )

        publisher.set_region.assert_called_once_with('us-east-2')

        assert publisher.publish_images.call_count == 1
        assert self.job.status == 'success'

    @patch.object(PublisherJob, 'send_log')
    @patch('mash.services.publisher.ec2_job.EC2PublishImage')
    def test_publish_exception(
        self, mock_ec2_publish_image, mock_send_log
    ):
        publisher = Mock()
        publisher.publish_images.side_effect = Exception('Failed to publish.')
        mock_ec2_publish_image.return_value = publisher

        self.job.source_regions = {'us-east-2': 'ami-123456'}

        msg = 'An error publishing image ami-123456 in us-east-2.' \
            ' Failed to publish.'
        with raises(MashPublisherException) as e:
            self.job._publish()
        assert msg == str(e.value)

    def test_validate_share_with(self):
        share_with = self.job.validate_share_with('123456789987,321456543342')
        assert share_with == '123456789987,321456543342'

        msg = 'Share with must be "all", "none", or comma separated list' \
              ' of 12 digit AWS account numbers.'
        with raises(MashPublisherException) as e:
            self.job.validate_share_with([''])

        assert msg == str(e.value)

        with raises(MashPublisherException) as e:
            self.job.validate_share_with(',')
