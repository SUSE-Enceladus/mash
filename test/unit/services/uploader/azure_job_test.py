from pytest import raises
from unittest.mock import (
    MagicMock,
    patch
)

from mash.services.uploader.azure_job import AzureUploaderJob
from mash.mash_exceptions import MashUploadException
from mash.services.uploader.config import UploaderConfig


class TestAzureUploaderJob(object):
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
            'last_service': 'uploader',
            'cloud': 'azure',
            'requesting_user': 'user1',
            'utctime': 'now',
            'account': 'test',
            'resource_group': 'group_name',
            'container': 'container',
            'storage_account': 'storage',
            'region': 'region',
            'cloud_image_name': 'name'
        }

        self.config = UploaderConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureUploaderJob(job_doc, self.config)
        self.job.image_file = 'file.vhdfixed.xz'
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'uploader',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AzureUploaderJob(job_doc, self.config)

    @patch('mash.services.uploader.azure_job.upload_azure_image')
    @patch('mash.services.uploader.azure_job.Process')
    @patch('mash.services.uploader.azure_job.SimpleQueue')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_queue, mock_process, mock_upload_azure_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        queue = MagicMock()
        queue.empty.return_value = True
        mock_queue.return_value = queue

        self.job.run_job()

        mock_process.assert_called_once_with(
            target=mock_upload_azure_image,
            args=(
                'name.vhd',
                'container',
                'file.vhdfixed.xz',
                5,
                8,
                'storage',
                queue,
                self.credentials['test'],
                'group_name',
                None
            )
        )

        # Test sas upload route
        self.job.sas_token = 'sas_token'
        mock_process.reset_mock()

        self.job.run_job()
        mock_process.assert_called_once_with(
            target=mock_upload_azure_image,
            args=(
                'name.vhd',
                'container',
                'file.vhdfixed.xz',
                5,
                8,
                'storage',
                queue,
                None,
                'group_name',
                'sas_token'
            )
        )

        queue.empty.return_value = False
        queue.get.return_value = 'Failed!'
        with raises(MashUploadException):
            self.job.run_job()
