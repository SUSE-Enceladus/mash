from pytest import raises
from unittest.mock import (
    MagicMock,
    patch,
    call
)

from mash.services.upload.azure_raw_job import AzureRawUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestAzureRawUploadJob(object):
    def setup_method(self):
        self.credentials = {
            'test': {
                'clientId': 'a',
                'clientSecret': 'b',
                'subscriptionId': 'c',
                'tenantId': 'd',
                'activeDirectoryEndpointUrl':
                    'https://login.microsoftonline.com',
                'resourceManagerEndpointUrl':
                    'https://management.azure.com/',
                'activeDirectoryGraphResourceId':
                    'https://graph.windows.net/',
                'sqlManagementEndpointUrl':
                    'https://management.core.windows.net:8443/',
                'galleryEndpointUrl':
                    'https://gallery.azure.com/',
                'managementEndpointUrl':
                    'https://management.core.windows.net/'
            }
        }
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'cloud': 'azure_raw',
            'requesting_user': 'user1',
            'utctime': 'now',
            'account': 'test',
            'resource_group': 'group_name',
            'container': 'container',
            'storage_account': 'storage',
            'region': 'region',
            'cloud_image_name': 'name',
            'additional_uploads': ['sha256.asc']
        }

        self.config = UploadConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureRawUploadJob(job_doc, self.config)
        self.job.status_msg['image_file'] = 'file.vhdfixed.xz'
        self.job.credentials = self.credentials
        self.job._log_callback = MagicMock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AzureRawUploadJob(job_doc, self.config)

    @patch('mash.services.upload.azure_raw_job.AzureImage')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        client = MagicMock()
        mock_azure_image.return_value = client

        self.job.run_job()

        client.upload_image_blob.assert_has_calls([
            call(
                'file.vhdfixed.xz.sha256.asc',
                max_workers=8,
                max_attempts=5,
                blob_name='file.vhdfixed.xz.sha256.asc',
                is_page_blob=False,
                expand_image=False
            ),
            call(
                'file.vhdfixed.xz',
                max_workers=8,
                max_attempts=5,
                blob_name='file.vhdfixed.xz',
                is_page_blob=False,
                expand_image=False
            )
        ])
