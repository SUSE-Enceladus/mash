from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashDeprecateException
from mash.services.deprecate.ec2_job import EC2DeprecateJob


class TestEC2DeprecateJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecate',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'old_cloud_image_name': 'old_image_123',
            'deprecate_regions': [
                {
                    'account': 'test-aws',
                    'target_regions': ['us-east-2']
                }
            ],
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = EC2DeprecateJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'test-aws': {
                'access_key_id': '123456',
                'secret_access_key': '654321'
            }
        }
        self.job.source_regions = {
            'cloud_image_name': 'image_123',
            'us-east-2': 'ami-123456'
        }

    def test_deprecate_ec2_missing_key(self):
        del self.job_config['deprecate_regions']

        with raises(MashDeprecateException):
            EC2DeprecateJob(self.job_config, self.config)

    @patch('mash.services.deprecate.ec2_job.EC2DeprecateImg')
    def test_deprecate(self, mock_ec2_deprecate_image):
        deprecate = Mock()
        mock_ec2_deprecate_image.return_value = deprecate

        self.job.run_job()

        mock_ec2_deprecate_image.assert_called_once_with(
            access_key='123456', deprecate_image_name='old_image_123',
            replacement_image_name='image_123', secret_key='654321',
            log_callback=self.job._log_callback
        )

        deprecate.set_region.assert_called_once_with('us-east-2')

        assert deprecate.deprecate_images.call_count == 1
        assert self.job.status == 'success'

    def test_deprecate_no_old_image(self):
        self.job.source_regions = {'us-east-2': 'ami-123456'}
        self.job.old_cloud_image_name = None
        self.job.run_job()
        assert self.job.status == 'success'

    @patch('mash.services.deprecate.ec2_job.EC2DeprecateImg')
    def test_deprecate_exception(self, mock_ec2_deprecate_image):
        deprecate = Mock()
        deprecate.deprecate_images.side_effect = Exception(
            'No images to deprecate.'
        )
        mock_ec2_deprecate_image.return_value = deprecate

        msg = 'Error deprecating image old_image_123 in us-east-2.' \
            ' No images to deprecate.'
        with raises(MashDeprecateException) as e:
            self.job.run_job()
        assert msg == str(e.value)

    @patch('mash.services.deprecate.ec2_job.EC2DeprecateImg')
    def test_deprecate_false(
        self, mock_ec2_deprecate_image
    ):
        deprecate = Mock()
        deprecate.deprecate_images.return_value = False
        mock_ec2_deprecate_image.return_value = deprecate

        self.job.run_job()

        self.job._log_callback.warning.assert_called_once_with(
            'Unable to deprecate image in us-east-2, no image found.'
        )
