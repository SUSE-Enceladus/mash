from pytest import raises
from unittest.mock import (
    MagicMock,
    patch
)

from mash.services.uploader.azure_sas_job import AzureSASUploaderJob
from mash.mash_exceptions import MashUploadException
from mash.services.uploader.config import UploaderConfig


class TestAzureSASUploaderJob(object):
    def setup(self):
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'cloud': 'azure',
            'requesting_user': 'user1',
            'utctime': 'now',
            'cloud_image_name': 'name',
            'raw_image_upload_location': 'https://storage.[maangement-url]/container?sas_token'
        }

        self.config = UploaderConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureSASUploaderJob(job_doc, self.config)
        self.job.image_file = 'file.vhdfixed.xz'
        self.job._log_callback = MagicMock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'requesting_user': 'user1',
            'cloud': 'azure',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AzureSASUploaderJob(job_doc, self.config)

    @patch('mash.services.uploader.azure_sas_job.upload_azure_image')
    @patch('builtins.open')
    def test_sas_upload_only(
        self, mock_open, mock_upload_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        self.job.run_job()
        mock_upload_azure_image.assert_called_once_with(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            5,
            8,
            'storage',
            sas_token='sas_token'
        )

    @patch('mash.services.uploader.azure_sas_job.upload_azure_image')
    @patch('builtins.open')
    def test_sas_upload(
        self, mock_open, mock_upload_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        self.job.source_regions = self.job.source_regions = {
            'cloud_image_name': 'name',
            'blob_name': 'name.vhd'
        }
        self.job.cloud_image_name = ''

        self.job.run_job()
        mock_upload_azure_image.assert_called_once_with(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            5,
            8,
            'storage',
            sas_token='sas_token'
        )
