from pytest import raises
from unittest.mock import (
    MagicMock,
    patch
)

from mash.services.upload.azure_sas_job import AzureSASUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestAzureSASUploadJob(object):
    def setup_method(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'cloud': 'azure',
            'requesting_user': 'user1',
            'utctime': 'now',
            'cloud_image_name': 'name',
            'raw_image_upload_location': 'https://storage.[maangement-url]/container?sas_token'
        }

        self.config = UploadConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureSASUploadJob(job_doc, self.config)
        self.job.status_msg = {'image_file': 'file.vhdfixed.xz'}
        self.job._log_callback = MagicMock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'azure',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AzureSASUploadJob(job_doc, self.config)

    @patch('mash.services.upload.azure_sas_job.AzureImage')
    @patch('builtins.open')
    def test_sas_upload_only(
        self, mock_open, mock_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        client = MagicMock()
        mock_azure_image.return_value = client

        self.job.run_job()
        client.upload_image_blob.assert_called_once_with(
            image_file='file.vhdfixed.xz',
            max_workers=8,
            max_attempts=5,
            blob_name='name.vhd',
            is_page_blob=True
        )

    @patch('mash.services.upload.azure_sas_job.AzureImage')
    @patch('builtins.open')
    def test_sas_upload(
        self, mock_open, mock_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        client = MagicMock()
        mock_azure_image.return_value = client

        self.job.status_msg['cloud_image_name'] = 'name'
        self.job.status_msg['blob_name'] = 'name.vhd'
        self.job.cloud_image_name = ''

        self.job.run_job()
        client.upload_image_blob.assert_called_once_with(
            image_file='file.vhdfixed.xz',
            max_workers=8,
            max_attempts=5,
            blob_name='name.vhd',
            is_page_blob=True
        )
