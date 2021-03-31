from pytest import raises
from unittest.mock import (
    MagicMock,
    patch
)

from mash.services.upload.azure_job import AzureUploadJob
from mash.mash_exceptions import MashUploadException
from mash.services.upload.config import UploadConfig


class TestAzureUploadJob(object):
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

    @patch('mash.services.upload.azure_job.delete_blob')
    @patch('mash.services.upload.azure_job.blob_exists')
    @patch('mash.services.upload.azure_job.upload_azure_file')
    @patch('builtins.open')
    def test_upload(
        self,
        mock_open,
        mock_upload_azure_file,
        mock_blob_exists,
        mock_delete_blob
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle
        mock_blob_exists.return_value = False

        self.job.run_job()

        mock_upload_azure_file.assert_called_once_with(
            'name v20200925.vhd',
            'container',
            'file.vhdfixed.xz',
            'storage',
            max_retry_attempts=5,
            max_workers=8,
            credentials=self.credentials['test'],
            resource_group='group_name',
            is_page_blob=True
        )

        # Blob exists no force replace
        mock_blob_exists.return_value = True
        with raises(MashUploadException):
            self.job.run_job()

        # Blob exists and force replace
        self.job.force_replace_image = True
        self.job.run_job()

        assert mock_delete_blob.call_count == 1
