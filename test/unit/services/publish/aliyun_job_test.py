from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublishException
from mash.services.publish.aliyun_job import AliyunPublishJob


class TestAliyunPublishJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'account': 'acnt1',
            'region': 'cn-beijing',
            'bucket': 'images',
            'launch_permission': 'PERMISSION',
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = AliyunPublishJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'acnt1': {
                'access_key': '123456',
                'access_secret': '654321'
            }
        }
        self.job.status_msg['cloud_image_name'] = 'image_name_123'
        self.job.status_msg['source_regions'] = {'cn-beijing': 'image-id'}
        self.job._log_callback = Mock()

    def test_publish_aliyun_missing_key(self):
        del self.job_config['bucket']

        with raises(MashPublishException):
            AliyunPublishJob(self.job_config, self.config)

    @patch('mash.services.publish.aliyun_job.AliyunImage')
    def test_publish(self, mock_aliyun_image):
        aliyun_image = Mock()
        aliyun_image.get_regions.return_value = ['cn-beijing']
        mock_aliyun_image.return_value = aliyun_image
        self.job.run_job()

        aliyun_image.publish_image.assert_called_once_with(
            'image_name_123',
            'PERMISSION'
        )

        assert self.job.status == 'success'

    @patch('mash.services.publish.aliyun_job.AliyunImage')
    def test_publish_exception(
        self, mock_aliyun_image
    ):
        aliyun_image = Mock()
        aliyun_image.get_regions.return_value = ['cn-beijing']
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.publish_image.side_effect = Exception(
            'Invalid credentials.'
        )

        self.job.run_job()
        self.job._log_callback.warning.assert_called_once_with(
            'Failed to publish image_name_123 in cn-beijing: Invalid credentials.'
        )
