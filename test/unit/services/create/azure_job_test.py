from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.create.azure_job import AzureCreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestAzureCreateJob(object):
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
            'last_service': 'create',
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

        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureCreateJob(job_doc, self.config)
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'create',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            AzureCreateJob(job_doc, self.config)

    @patch('mash.services.create.azure_job.get_client_from_auth_file')
    @patch('builtins.open')
    def test_create(
        self, mock_open, mock_get_client_from_auth_file
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        client = MagicMock()
        mock_get_client_from_auth_file.return_value = client

        async_create_image = Mock()
        client.images.create_or_update.return_value = async_create_image

        self.job.source_regions = self.job.source_regions = {
            'region': {
                'cloud_image_name': 'name',
                'blob_name': 'name.vhd'
            }
        }
        self.job.run_job()

        assert mock_get_client_from_auth_file.call_count == 1
        client.images.create_or_update.assert_called_once_with(
            'group_name', 'name', {
                'location': 'region',
                'hyper_vgeneration': 'V1',
                'storage_profile': {
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
