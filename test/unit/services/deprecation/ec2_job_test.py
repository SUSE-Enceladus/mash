from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashDeprecationException
from mash.services.deprecation.ec2_job import EC2DeprecationJob


class TestEC2DeprecationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecation',
            'cloud': 'ec2',
            'old_cloud_image_name': 'old_image_123',
            'deprecation_regions': [
                {
                    'account': 'test-aws',
                    'target_regions': ['us-east-2']
                }
            ],
            'utctime': 'now'
        }

        self.job = EC2DeprecationJob(self.job_config)
        self.job.credentials = {
            'test-aws': {
                'access_key_id': '123456',
                'secret_access_key': '654321'
            }
        }

    @patch('mash.services.deprecation.ec2_job.EC2DeprecateImg')
    def test_deprecate(self, mock_ec2_deprecate_image):
        deprecation = Mock()
        mock_ec2_deprecate_image.return_value = deprecation

        self.job.source_regions = {'us-east-2': 'ami-123456'}
        self.job._run_job()

        mock_ec2_deprecate_image.assert_called_once_with(
            access_key='123456', deprecation_image_name='old_image_123',
            replacement_image_name=None, secret_key='654321',
            verbose=False
        )

        deprecation.set_region.assert_called_once_with('us-east-2')

        assert deprecation.deprecate_images.call_count == 1
        assert self.job.status == 'success'

    def test_deprecate_no_old_image(self):
        self.job.source_regions = {'us-east-2': 'ami-123456'}
        self.job.old_cloud_image_name = None
        self.job._run_job()
        assert self.job.status == 'success'

    @patch.object(EC2DeprecationJob, 'send_log')
    @patch('mash.services.deprecation.ec2_job.EC2DeprecateImg')
    def test_deprecate_exception(
        self, mock_ec2_deprecate_image, mock_send_log
    ):
        deprecation = Mock()
        deprecation.deprecate_images.return_value = False
        mock_ec2_deprecate_image.return_value = deprecation

        self.job.source_regions = {'us-east-2': 'ami-123456'}

        msg = 'Error deprecating image old_image_123 in us-east-2.' \
            ' No images to deprecate.'
        with raises(MashDeprecationException) as e:
            self.job._run_job()
        assert msg == str(e.value)
