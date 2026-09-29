from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashReplicateException
from mash.services.status_levels import FAILED
from mash.services.replicate.aliyun_job import AliyunReplicateJob


class TestAliyunReplicateJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'bucket': 'images',
            'last_service': 'replicate',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'account': 'acnt1',
            'utctime': 'now',
            "region": "cn-beijing"
        }

        self.config = Mock()
        self.config.get_aliyun_ignored_regions.return_value = ['region1']
        self.job = AliyunReplicateJob(self.job_config, self.config)
        self.job._log_callback = Mock()

        self.job.credentials = {
            "acnt1": {
                'access_key': '123456',
                'access_secret': '654321'
            }
        }

        self.job.status_msg['cloud_image_name'] = 'My image'
        self.job.status_msg['source_regions'] = {'cn-beijing': 'ami-12345'}

    def test_replicate_aliyun_missing_key(self):
        del self.job_config['bucket']

        with raises(MashReplicateException):
            AliyunReplicateJob(self.job_config, self.config)

    @patch('mash.services.replicate.aliyun_job.time')
    @patch('mash.services.replicate.aliyun_job.AliyunImage')
    def test_replicate(self, mock_aliyun_image, mock_time):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.replicate_image.return_value = {'cn-shanghai': None}

        self.job.run_job()

        mock_aliyun_image.assert_called_once_with(
            '123456',
            '654321',
            'cn-beijing',
            'images',
            log_callback=self.job.log_callback,
            ignored_regions=['region1']
        )

        self.job._log_callback.info.assert_called_once_with(
            'Replicating My image'
        )
        self.job._log_callback.warning.assert_called_once_with(
            'Replicate to cn-shanghai failed: Image ID is None'
        )
        assert self.job.status == FAILED

    @patch('mash.services.replicate.aliyun_job.time')
    @patch('mash.services.replicate.aliyun_job.AliyunImage')
    def test_replicate_fail(self, mock_aliyun_image, mock_time):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.replicate_image.return_value = {'cn-shanghai': 'i-8765'}
        aliyun_image.wait_on_compute_image.side_effect = Exception('Broken!')

        self.job.run_job()

        mock_aliyun_image.assert_called_once_with(
            '123456',
            '654321',
            'cn-beijing',
            'images',
            log_callback=self.job.log_callback,
            ignored_regions=['region1']
        )

        self.job._log_callback.info.assert_called_once_with(
            'Replicating My image'
        )
        self.job._log_callback.warning.assert_called_once_with(
            'Replicate to cn-shanghai failed: Broken!'
        )
        assert self.job.status == FAILED
