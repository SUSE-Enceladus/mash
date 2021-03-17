from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashDeprecateException
from mash.services.deprecate.aliyun_job import AliyunDeprecateJob


class TestAliyunDeprecateJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecate',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'cloud_account': 'acnt1',
            'region': 'cn-beijing',
            'bucket': 'images',
            'old_cloud_image_name': 'old-image-123',
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = AliyunDeprecateJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'acnt1': {
                'access_key': '123456',
                'access_secret': '654321'
            }
        }
        self.job._log_callback = Mock()

    def test_deprecate_aliyun_missing_key(self):
        del self.job_config['bucket']

        with raises(MashDeprecateException):
            AliyunDeprecateJob(self.job_config, self.config)

    @patch('mash.services.deprecate.aliyun_job.AliyunImage')
    def test_deprecate(self, mock_aliyun_image):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        self.job.run_job()

        aliyun_image.deprecate_image_in_regions.assert_called_once_with(
            'old-image-123'
        )

        assert self.job.status == 'success'

    @patch('mash.services.deprecate.aliyun_job.AliyunImage')
    def test_deprecate_exception(
        self, mock_aliyun_image
    ):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.deprecate_image_in_regions.side_effect = Exception(
            'Invalid credentials.'
        )

        msg = 'Failed to deprecate image old-image-123: Invalid credentials.'
        with raises(MashDeprecateException) as e:
            self.job.run_job()
        assert msg == str(e.value)

    @patch('mash.services.deprecate.aliyun_job.AliyunImage')
    def test_no_deprecate(
        self, mock_aliyun_image
    ):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        self.job.old_cloud_image_name = None
        self.job.run_job()
