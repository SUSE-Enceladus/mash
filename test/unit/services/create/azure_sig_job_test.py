from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch, call
)

from mash.services.create.azure_sig_job import AzureSIGCreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestAzureSIGCreateJob(object):
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
            'boot_firmware': ['bios', 'uefi'],
            'gallery_name': 'gallery1',
            'sku': 'gen1',
            'offer_id': 'sles-15-sp3',
            'generation_id': 'gen2'
        }

        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.job = AzureSIGCreateJob(job_doc, self.config)
        self.job.credentials = self.credentials
        self.job._log_callback = Mock()

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'create',
            'requesting_user': 'user1',
            'cloud': 'azure_sig',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            AzureSIGCreateJob(job_doc, self.config)

    @patch('mash.services.create.azure_sig_job.AzureImage')
    @patch('builtins.open')
    def test_create(
        self,
        mock_open,
        mock_azure_image,
    ):
        azure_image = MagicMock()
        mock_azure_image.return_value = azure_image

        self.job.status_msg['cloud_image_name'] = 'image-123-v20220202'
        self.job.status_msg['blob_name'] = 'name.vhd'
        self.job.run_job()

        azure_image.create_gallery_image_version.assert_has_calls([
            call(
                blob_name='name.vhd',
                gallery_name='gallery1',
                gallery_image_name='sles_15_sp3_gen1',
                image_version='2022.02.02',
                region='region',
                force_replace_image=True,
                gallery_resource_group='group_name'
            ),
            call(
                blob_name='name.vhd',
                gallery_name='gallery1',
                gallery_image_name='sles_15_sp3_gen2',
                image_version='2022.02.02',
                region='region',
                force_replace_image=True,
                gallery_resource_group='group_name'
            )
        ])
