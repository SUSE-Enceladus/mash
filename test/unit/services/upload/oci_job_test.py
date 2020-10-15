from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.upload.oci_job import OCIUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestOCIUploadJob(object):
    def setup(self):
        self.config = UploadConfig(
            config_file='test/data/mash_config.yaml'
        )

        credentials = {
            'test': {
                'signing_key': 'test key',
                'fingerprint': 'fake fingerprint'
            }
        }

        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'cloud': 'oci',
            'requesting_user': 'user1',
            'utctime': 'now',
            'region': 'us-phoenix-1',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-12-sp4-v{date}',
            'image_description': 'description 20200925',
            'oci_user_id': 'ocid1.user.oc1..',
            'tenancy': 'ocid1.tenancy.oc1..',
            'use_build_time': True
        }

        self.job = OCIUploadJob(job_doc, self.config)
        self.job.status_msg = {
            'image_file': 'sles-12-sp4-v20200925.qcow2',
            'build_time': '1601061355'
        }
        self.job.credentials = credentials
        self.job._log_callback = Mock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'oci',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            OCIUploadJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    @patch('mash.services.upload.oci_job.stat')
    @patch('mash.services.upload.oci_job.UploadManager')
    @patch('mash.services.upload.oci_job.ObjectStorageClient')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_storage_client, mock_upload_manager, mock_stat
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        image_info = Mock()
        image_info.st_size = 112358
        mock_stat.return_value = image_info

        namespace = Mock()
        namespace.data = 'namespace name'

        storage_driver = Mock()
        storage_driver.get_namespace.return_value = namespace

        mock_storage_client.return_value = storage_driver

        upload_manager = Mock()
        mock_upload_manager.return_value = upload_manager

        self.job.run_job()

        upload_manager.upload_stream.assert_called_once_with(
            'namespace name',
            'images',
            'sles-12-sp4-v20200925.qcow2',
            open_handle,
            progress_callback=self.job._progress_callback
        )

    def test_progress_callback(self):
        self.job._image_size = 112358
        self.job._progress_callback(400)

        self.job._log_callback.info.assert_called_once_with('Image 0% uploaded.')
        assert self.job._total_bytes_transferred == 400
