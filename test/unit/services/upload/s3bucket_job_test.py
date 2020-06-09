from pytest import raises
from unittest.mock import Mock, patch

from test.unit.test_helper import (
    patch_open
)

from mash.services.upload.s3bucket_job import S3BucketUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.base_config import BaseConfig


class TestS3BucketUploadJob(object):
    def setup(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'access_key_id': 'access-key',
                'secret_access_key': 'secret-access-key'
            }
        }
        job_doc = {
            'cloud_architecture': 'x86_64',
            'id': '1',
            'last_service': 'upload',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'utctime': 'now',
            'target_regions': {
                'us-east-1': {
                    'account': 'test',
                    'helper_image': 'ami-bc5b48d0',
                    'billing_codes': None,
                    'use_root_swap': False,
                    'subnet': 'subnet-123456789'
                }
            },
            'cloud_image_name': 'name',
            'image_description': 'description',
            'raw_image_upload_type': 's3bucket',
            'raw_image_upload_location': 'my-bucket/some-prefix/',
            'raw_image_upload_account': 'test'
        }
        self.job = S3BucketUploadJob(job_doc, self.config)
        self.job.image_file = 'file.raw.gz'
        self.job.cloud_image_name = 'name'
        self.job.credentials = self.credentials
        self.job._log_callback = Mock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            S3BucketUploadJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'name'
        with raises(MashUploadException):
            S3BucketUploadJob(job_doc, self.config)

    @patch('mash.services.upload.s3bucket_job.stat')
    @patch('mash.services.upload.s3bucket_job.get_client')
    @patch_open
    def test_upload(
        self, mock_request_credentials, mock_get_client, mock_stat
    ):
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        stat_info = Mock()
        stat_info.st_size = 100
        mock_stat.return_value = stat_info

        self.job.run_job()
        mock_get_client.assert_called_once_with(
            's3', 'access-key', 'secret-access-key', None,
        )
        mock_client.upload_file.assert_called_once_with(
            'file.raw.gz',
            'my-bucket',
            'some-prefix/name.raw.gz',
            Callback=self.job._log_progress
        )

        mock_client.upload_file.side_effect = Exception

        with raises(MashUploadException):
            self.job.run_job()

    def test_log_progress(self):
        self.job._image_size = 100
        self.job._log_progress(100)
        self.job._log_callback.info.assert_called_once_with(
            'Raw image 100% uploaded.'
        )
