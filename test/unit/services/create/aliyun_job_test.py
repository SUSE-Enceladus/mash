from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.create.aliyun_job import AliyunCreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestAliyunCreateJob(object):
    def setup(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'access_key': '123456789',
                'access_secret': '987654321'
            }
        }
        job_doc = {
            'id': '1',
            'last_service': 'create',
            'cloud': 'aliyun',
            'requesting_user': 'user1',
            'utctime': 'now',
            'platform': 'SUSE',
            'cloud_architecture': 'x86_64',
            'region': 'cn-beijing',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-15-sp2-v20210316',
            'image_description': 'great image description',
            'disk_size': 20
        }

        self.job = AliyunCreateJob(job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            AliyunCreateJob(job_doc, self.config)

    @patch('mash.services.create.aliyun_job.AliyunImage')
    def test_create(self, mock_aliyun_image):
        aliyun_image = MagicMock()
        mock_aliyun_image.return_value = aliyun_image

        self.job.status_msg['cloud_image_name'] = 'sles-15-sp2-v20210316'
        self.job.status_msg['object_name'] = 'sles-15-sp2-v20210316.qcow2'
        self.job.run_job()

        aliyun_image.delete_compute_image.assert_called_once_with(
            'sles-15-sp2-v20210316'
        )
        aliyun_image.create_compute_image.assert_called_once_with(
            'sles-15-sp2-v20210316',
            'great image description',
            'sles-15-sp2-v20210316.qcow2',
            platform='SUSE',
            cloud_architecture='x86_64',
            disk_image_size=20
        )
