from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.upload.aliyun_job import AliyunUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestAliyunUploadJob(object):
    def setup_method(self):
        self.config = UploadConfig(
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
            'last_service': 'upload',
            'cloud': 'aliyun',
            'requesting_user': 'user1',
            'utctime': 'now',
            'region': 'cn-beijing',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-15-sp2-v{date}',
            'image_description': 'great image description',
            'use_build_time': True
        }

        self.log_callback = Mock()
        self.job = AliyunUploadJob(job_doc, self.config)
        self.job.status_msg['image_file'] = 'sles-15-sp2-v20180909.qcow2'
        self.job.status_msg['build_time'] = '1601061355'
        self.job.credentials = self.credentials
        self.job._log_callback = self.log_callback

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'aliyun',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AliyunUploadJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    @patch('mash.services.upload.aliyun_job.AliyunImage')
    def test_upload(
        self,
        mock_aliyun_image
    ):
        aliyun_image = MagicMock()
        mock_aliyun_image.return_value = aliyun_image
        aliyun_image.image_tarball_exists.return_value = False

        self.job.run_job()
        assert aliyun_image.upload_image_tarball.call_count == 1

        # Tarball exists and no force replace
        aliyun_image.image_tarball_exists.return_value = True
        with raises(MashUploadException):
            self.job.run_job()

        # Tarball exists and force replace
        self.job.force_replace_image = True
        self.job.run_job()

        assert aliyun_image.delete_storage_blob.call_count == 1

    def test_progress_callback(self):
        self.job.progress_callback(0, 0, done=True)
        self.log_callback.info.assert_called_once_with(
            'Image upload finished.'
        )
        self.log_callback.info.reset_mock()

        self.job.progress_callback(100, 400)
        self.log_callback.info.assert_called_once_with(
            'Image 25% uploaded.'
        )
