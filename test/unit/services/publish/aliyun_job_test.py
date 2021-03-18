from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublishException
from mash.services.publish.aliyun_job import AliyunPublishJob


class TestAliyunPublishJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'cloud_account': 'acnt1',
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
        mock_aliyun_image.return_value = aliyun_image
        self.job.run_job()

        aliyun_image.publish_image_to_regions.assert_called_once_with(
            'image_name_123',
            'PERMISSION'
        )

        assert self.job.status == 'success'

    @patch('mash.services.publish.aliyun_job.AliyunImage')
    def test_publish_exception(
        self, mock_aliyun_image
    ):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.publish_image_to_regions.side_effect = Exception(
            'Invalid credentials.'
        )

        msg = 'Failed to publish image image_name_123: Invalid credentials.'
        with raises(MashPublishException) as e:
            self.job.run_job()
        assert msg == str(e.value)
