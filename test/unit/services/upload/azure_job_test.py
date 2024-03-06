from pytest import raises
from unittest.mock import (
    MagicMock,
    patch
)

from mash.services.upload.azure_job import AzureUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestAzureUploadJob(object):
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
            'cloud': 'azure',
            'requesting_user': 'user1',
            'utctime': 'now',
            'account': 'test',
            'resource_group': 'group_name',
            'container': 'container',
            'storage_account': 'storage',
            'region': 'region',
            'cloud_image_name': 'name v{date}',
            'use_build_time': True
        }

        self.config = UploadConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureUploadJob(job_doc, self.config)
        self.job.status_msg['image_file'] = 'file.vhdfixed.xz'
        self.job.status_msg['build_time'] = '1601061355'
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
            AzureUploadJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    @patch('mash.services.upload.azure_job.AzureImage')
    @patch('builtins.open')
    def test_upload(
        self,
        mock_open,
        mock_azure_image
    ):
        bsc = MagicMock()
        client = MagicMock()
        mock_azure_image.return_value = client
        client.blob_service_client = bsc

        self.job.force_replace_image = True
        self.job.run_job()

        client.upload_image_blob.assert_called_once_with(
            'file.vhdfixed.xz',
            max_workers=8,
            max_attempts=5,
            blob_name='name v20200925.vhd',
            force_replace_image=True
        )
