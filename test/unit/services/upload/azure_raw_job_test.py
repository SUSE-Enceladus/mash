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
    def setup(self):
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
        self.job.image_file = 'file.vhdfixed.xz'
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

    @patch('mash.services.upload.azure_raw_job.upload_azure_file')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_upload_azure_file
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        self.job.run_job()

        mock_upload_azure_file.assert_has_calls([
            call(
                'file.vhdfixed.xz.sha256.asc',
                'container',
                'file.vhdfixed.xz.sha256.asc',
                5,
                8,
                'storage',
                credentials=self.credentials['test'],
                resource_group='group_name',
                expand_image=False
            ),
            call(
                'file.vhdfixed.xz',
                'container',
                'file.vhdfixed.xz',
                5,
                8,
                'storage',
                credentials=self.credentials['test'],
                resource_group='group_name',
                expand_image=False
            )
        ])
