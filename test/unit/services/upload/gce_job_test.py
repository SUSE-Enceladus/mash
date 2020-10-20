from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.upload.gce_job import GCEUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestGCEUploadJob(object):
    def setup(self):
        self.config = UploadConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'type': 'type',
                'project_id': 'projectid',
                'private_key_id': 'keyid',
                'private_key': 'key',
                'client_email': 'b@email.com',
                'client_id': 'a',
                'auth_uri':
                    'https://accounts.google.com/o/oauth2/auth',
                'token_uri':
                    'https://accounts.google.com/o/oauth2/token',
                'auth_provider_x509_cert_url':
                    'https://www.googleapis.com/oauth2/v1/certs',
                'client_x509_cert_url':
                    'https://www.googleapis.com/robot/v1/metadata/x509/'
            }
        }
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'utctime': 'now',
            'family': 'sles-12',
            'guest_os_features': ['UEFI_COMPATIBLE'],
            'region': 'us-west1-a',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-12-sp4-v{date}',
            'image_description': 'description 20180909',
            'use_build_time': True
        }

        self.job = GCEUploadJob(job_doc, self.config)
        self.job.status_msg['image_file'] = 'sles-12-sp4-v20180909.tar.gz'
        self.job.status_msg['build_time'] = '1601061355'
        self.job.credentials = self.credentials
        self.job._log_callback = Mock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            GCEUploadJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    def test_post_init_sles_11(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'utctime': 'now',
            'family': 'sles-11',
            'guest_os_features': ['UEFI_COMPATIBLE'],
            'region': 'us-west1-a',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-11-sp4-v20180909',
            'image_description': 'description 20180909'
        }

        with raises(MashUploadException):
            GCEUploadJob(job_doc, self.config)

    @patch('mash.services.upload.gce_job.get_gce_storage_driver')
    @patch('mash.services.upload.gce_job.upload_image_tarball')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_upload_image, mock_get_driver
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        storage_driver = Mock()
        mock_get_driver.return_value = storage_driver

        self.job.run_job()

        assert mock_upload_image.call_count == 1
