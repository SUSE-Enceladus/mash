from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch, call
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
            'cloud_image_name': 'name',
            'boot_firmware': ['bios', 'uefi']
        }

        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureCreateJob(job_doc, self.config)
        self.job.credentials = self.credentials
        self.job._log_callback = Mock()

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

    @patch('mash.services.create.azure_job.AzureImage')
    @patch('builtins.open')
    def test_create(
        self,
        mock_open,
        mock_azure_image,
    ):
        azure_image = MagicMock()
        mock_azure_image.return_value = azure_image

        self.job.status_msg['cloud_image_name'] = 'name'
        self.job.status_msg['blob_name'] = 'name.vhd'
        self.job.run_job()

        azure_image.create_compute_image.assert_has_calls([
            call(
                blob_name='name.vhd',
                image_name='name',
                region='region',
                force_replace_image=True,
                hyper_v_generation='V1'
            ),
            call(
                blob_name='name.vhd',
                image_name='name_uefi',
                region='region',
                force_replace_image=True,
                hyper_v_generation='V2'
            )
        ])
