from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch, call
)
from test.unit.test_helper import (
    patch_open, context_manager
)
from collections import namedtuple

from mash.services.uploader.cloud.azure import UploadAzure
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat

from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient


class TestUploadAzure(object):
    @patch('mash.services.uploader.cloud.azure.NamedTemporaryFile')
    @patch_open
    def setup(self, mock_open, mock_NamedTemporaryFile):
        open_context = context_manager()
        mock_open.return_value = open_context.context_manager_mock
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
            'container_name': 'container',
            'storage_account': 'storage',
            'region': 'region'
        }
        self.uploader = UploadAzure(
            self.credentials, 'file', 'name', 'description', custom_args
        )
        open_context.file_mock.write.assert_called_once_with(
            JsonFormat.json_message(self.credentials)
        )

    @patch('mash.services.uploader.cloud.azure.NamedTemporaryFile')
    @patch_open
    def test_init_incomplete_arguments(
        self, mock_open, mock_NamedTemporaryFile
    ):
        custom_args = {
            'resource_group': 'group_name',
            'container_name': 'container',
            'storage_account': 'storage',
            'region': 'region'
        }
        del custom_args['storage_account']
        with raises(MashUploadException):
            UploadAzure(
                self.credentials, 'file', 'name', 'description', custom_args
            )
        del custom_args['container_name']
        with raises(MashUploadException):
            UploadAzure(
                self.credentials, 'file', 'name', 'description', custom_args
            )
        del custom_args['region']
        with raises(MashUploadException):
            UploadAzure(
                self.credentials, 'file', 'name', 'description', custom_args
            )
        with raises(MashUploadException):
            UploadAzure(
                self.credentials, 'file', 'name', 'description', None
            )

    @patch('mash.services.uploader.cloud.azure.get_client_from_auth_file')
    @patch('mash.services.uploader.cloud.azure.PageBlobService')
    def test_upload(
        self, mock_PageBlobService, mock_get_client_from_auth_file
    ):
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
        page_blob_service.create_blob_from_path.assert_called_once_with(
            'container', 'name', 'file', max_connections=4
        )
        client.images.create_or_update.assert_called_once_with(
            'group_name', 'name', {
                'location': 'region', 'storage_profile': {
                    'os_disk': {
                        'blob_uri':
                        'https://storage.blob.core.windows.net/container/name',
                        'os_type': 'Linux',
                        'caching': 'ReadWrite',
                        'os_state': 'Generalized'
                    }
                }
            }
        )
        async_create_image.wait.assert_called_once_with()
