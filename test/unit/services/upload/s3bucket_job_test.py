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
            'raw_image_upload_account': 'test',
            'status_msg': {
                'build_time': '1677149451'
            }
        }
        self.job = S3BucketUploadJob(job_doc, self.config)
        self.job.status_msg = {
            'image_file': 'file.raw.gz',
            'cloud_image_name': 'name'
        }
        self.job.credentials = self.credentials
        self.job._log_callback = Mock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now',
            'raw_image_upload_account': "account1",
        }

        with raises(MashUploadException) as e:
            S3BucketUploadJob(job_doc, self.config)
        assert "S3 bucket upload jobs require a(n)" in str(e)
        assert "raw_image_upload_location" in str(e)

        job_doc['use_build_time'] = True
        job_doc['raw_image_upload_location'] = 'bucket1'

        with raises(MashUploadException) as e:
            S3BucketUploadJob(job_doc, self.config)
        assert "When use_build_time flag is True the {date}" in str(e)

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

        # Test bucket only location
        mock_client.upload_file.reset_mock()
        self.job.location = 'my-bucket'
        self.job.run_job()

        mock_client.upload_file.assert_called_once_with(
            'file.raw.gz',
            'my-bucket',
            'name.raw.gz',
            Callback=self.job._log_progress
        )

        # test use_build_time in location
        mock_client.upload_file.reset_mock()
        self.job.location = 'my-bucket/filename_v{date}.tar.gz'
        self.job.account = 'test'
        self.job.use_build_time = True
        self.job.status_msg['build_time'] = '1677149451'
        self.job.status_msg['image_file'] = 'file.raw.gz'
        self.job.run_job()
        mock_client.upload_file.assert_called_once_with(
            'file.raw.gz',
            'my-bucket',
            'filename_v20230223.tar.gz',
            Callback=self.job._log_progress
        )
        assert self.job.status_msg['key_name'] == 'filename_v20230223.tar.gz'
        assert self.job.status_msg['bucket_name'] == 'my-bucket'

        # Test exception in use_build_time
        mock_client.upload_file.reset_mock()
        del self.job.status_msg['build_time']
        with raises(MashUploadException) as e:
            self.job.run_job()
        assert "use_build_time set for job but build time is unknown" in str(e)

        # Test bucket and full name
        mock_client.upload_file.reset_mock()
        self.job.location = 'my-bucket/some-prefix/image.raw.gz'
        self.job.status_msg['cloud_image_name'] = None
        self.job.use_build_time = False
        self.job.run_job()

        mock_client.upload_file.assert_called_once_with(
            'file.raw.gz',
            'my-bucket',
            'some-prefix/image.raw.gz',
            Callback=self.job._log_progress
        )

        # Test upload exception
        mock_client.upload_file.side_effect = Exception

        self.job.use_build_time = False
        with raises(MashUploadException):
            self.job.run_job()

    def test_log_progress(self):
        self.job._image_size = 100
        self.job._log_progress(100)
        self.job._log_callback.info.assert_called_once_with(
            'Raw image 100% uploaded.'
        )
