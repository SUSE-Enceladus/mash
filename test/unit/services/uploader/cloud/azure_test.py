import io
from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch, call
)
from collections import namedtuple

from mash.services.uploader.cloud.azure import UploadAzure
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat
from mash.services.uploader.config import UploaderConfig
from mash.services.base_defaults import Defaults

from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient


class TestUploadAzure(object):
    @patch('mash.services.uploader.cloud.azure.NamedTemporaryFile')
    @patch('mash.services.uploader.cloud.azure.get_configuration')
    def setup(self, mock_get_configuration, mock_NamedTemporaryFile):
        tempfile = Mock()
        tempfile.name = 'tempfile'
        mock_NamedTemporaryFile.return_value = tempfile
        self.credentials = Mock()
        self.credentials = {
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
        custom_args = {
            'resource_group': 'group_name',
            'container': 'container',
            'storage_account': 'storage',
            'region': 'region'
        }
        mock_get_configuration.return_value = UploaderConfig(
            config_file='../data/empty_mash_config.yaml'
        )
        with patch('builtins.open', create=True):
            self.uploader = UploadAzure(
                self.credentials, 'file.vhdfixed.xz',
                'name', 'description', custom_args, 'x86_64'
            )
            config = self.uploader.config
            assert config.get_azure_max_retry_attempts() == \
                Defaults.get_azure_max_retry_attempts()
            assert config.get_azure_max_workers() == \
                Defaults.get_azure_max_workers()
        mock_get_configuration.return_value = UploaderConfig(
            config_file='../data/mash_config.yaml'
        )
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            self.uploader = UploadAzure(
                self.credentials, 'file.vhdfixed.xz',
                'name', 'description', custom_args,
                'x86_64'
            )
            file_handle.write.assert_called_once_with(
                JsonFormat.json_message(self.credentials)
            )

    @patch('mash.services.uploader.cloud.azure.NamedTemporaryFile')
    def test_init_incomplete_arguments(self, mock_NamedTemporaryFile):
        custom_args = {
            'resource_group': 'group_name',
            'container': 'container',
            'storage_account': 'storage',
            'region': 'region'
        }
        with patch('builtins.open', create=True):
            del custom_args['storage_account']
            with raises(MashUploadException):
                UploadAzure(
                    self.credentials, 'file.vhdfixed.xz',
                    'name', 'description', custom_args, 'x86_64'
                )
            del custom_args['container']
            with raises(MashUploadException):
                UploadAzure(
                    self.credentials, 'file.vhdfixed.xz',
                    'name', 'description', custom_args, 'x86_64'
                )
            del custom_args['region']
            with raises(MashUploadException):
                UploadAzure(
                    self.credentials, 'file.vhdfixed.xz',
                    'name', 'description', custom_args, 'x86_64'
                )
            with raises(MashUploadException):
                UploadAzure(
                    self.credentials, 'file.vhdfixed.xz',
                    'name', 'description', None, 'x86_64'
                )

    @patch('mash.services.uploader.cloud.azure.get_client_from_auth_file')
    @patch('mash.services.uploader.cloud.azure.PageBlobService')
    @patch('mash.services.uploader.cloud.azure.FileType')
    @patch('mash.services.uploader.cloud.azure.lzma')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_lzma, mock_FileType,
        mock_PageBlobService, mock_get_client_from_auth_file
    ):
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

        assert self.uploader.upload() == ('name', 'region')

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
            self.uploader.upload()
