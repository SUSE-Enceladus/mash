from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch, call
)
from collections import namedtuple

from mash.services.uploader.azure_job import AzureUploaderJob
from mash.mash_exceptions import MashUploadException
from mash.services.uploader.config import UploaderConfig

from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient


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
            'utctime': 'now',
            'target_regions': {
                'region': {
                    'account': 'test',
                    'resource_group': 'group_name',
                    'container': 'container',
                    'storage_account': 'storage',
                }
            },
            'cloud_image_name': 'name'
        }

        self.config = UploaderConfig(
            config_file='../data/mash_config.yaml'
        )

        self.job = AzureUploaderJob(job_doc, self.config)
        self.job.image_file = ['file.vhdfixed.xz']
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'uploader',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            AzureUploaderJob(job_doc, self.config)

        job_doc['target_regions'] = {'name': {'account': 'info'}}
        with raises(MashUploadException):
            AzureUploaderJob(job_doc, self.config)

    @patch('mash.services.uploader.azure_job.NamedTemporaryFile')
    @patch('mash.services.uploader.azure_job.get_client_from_auth_file')
    @patch('mash.services.uploader.azure_job.PageBlobService')
    @patch('mash.services.uploader.azure_job.FileType')
    @patch('mash.services.uploader.azure_job.lzma')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_lzma, mock_FileType,
        mock_PageBlobService, mock_get_client_from_auth_file,
        mock_NamedTemporaryFile
    ):
        tempfile = Mock()
        tempfile.name = 'tempfile'
        mock_NamedTemporaryFile.return_value = tempfile

        lzma_handle = MagicMock()
        lzma_handle.__enter__.return_value = lzma_handle
        mock_lzma.LZMAFile.return_value = lzma_handle

        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        client = MagicMock()
        mock_get_client_from_auth_file.return_value = client

        page_blob_service = Mock()
        mock_PageBlobService.return_value = page_blob_service

        key_type = namedtuple('key_type', ['value', 'key_name'])
        async_create_image = Mock()
        storage_key_list = Mock()
        storage_key_list.keys = [
            key_type(value='key', key_name='key_name')
        ]

        client.storage_accounts.list_keys.return_value = storage_key_list
        client.images.create_or_update.return_value = async_create_image

        system_image_file_type = Mock()
        system_image_file_type.get_size.return_value = 1024
        system_image_file_type.is_xz.return_value = True
        mock_FileType.return_value = system_image_file_type

        self.job._run_job()

        assert mock_get_client_from_auth_file.call_args_list == [
            call(StorageManagementClient, auth_path='tempfile'),
            call(ComputeManagementClient, auth_path='tempfile')
        ]
        client.storage_accounts.list_keys.assert_called_once_with(
            'group_name', 'storage'
        )
        mock_PageBlobService.assert_called_once_with(
            account_key='key', account_name='storage'
        )
        mock_FileType.assert_called_once_with('file.vhdfixed.xz')
        system_image_file_type.is_xz.assert_called_once_with()
        page_blob_service.create_blob_from_stream.assert_called_once_with(
            'container', 'name.vhd', lzma_handle, 1024,
            max_connections=8
        )
        client.images.create_or_update.assert_called_once_with(
            'group_name', 'name', {
                'location': 'region', 'storage_profile': {
                    'os_disk': {
                        'blob_uri':
                        'https://storage.blob.core.windows.net/'
                        'container/name.vhd',
                        'os_type': 'Linux',
                        'caching': 'ReadWrite',
                        'os_state': 'Generalized'
                    }
                }
            }
        )
        async_create_image.wait.assert_called_once_with()

        system_image_file_type.is_xz.return_value = False
        page_blob_service.create_blob_from_stream.side_effect = Exception

        with raises(MashUploadException):
            self.job._run_job()
