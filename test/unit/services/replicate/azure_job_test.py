from pytest import raises
from unittest.mock import call, patch, Mock

from mash.services.status_levels import FAILED
from mash.services.replicate.azure_job import AzureReplicateJob
from mash.mash_exceptions import MashReplicateException


class TestAzureReplicateJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'image_description': 'My image',
            'last_service': 'replicate',
            'requesting_user': 'user1',
            'cloud': 'azure',
            'utctime': 'now',
            'account': 'acnt1',
            'source_resource_group': 'rg-1',
            'source_container': 'container1',
            'source_storage_account': 'sa1',
            'region': 'East US',
            'destination_resource_group': 'rg-2',
            'destination_container': 'container2',
            'destination_storage_account': 'sa2',
            "cleanup_images": True
        }

        self.config = Mock()
        self.job = AzureReplicateJob(self.job_config, self.config)

        self.job.credentials = {
            "acnt1": {
                "clientId": "09876543-1234-1234-1234-123456789012",
                "clientSecret": "09876543-1234-1234-1234-123456789012",
                "subscriptionId": "09876543-1234-1234-1234-123456789012",
                "tenantId": "09876543-1234-1234-1234-123456789012",
                "activeDirectoryEndpointUrl":
                    "https://login.microsoftonline.com",
                "resourceManagerEndpointUrl": "https://management.azure.com/",
                "activeDirectoryGraphResourceId":
                    "https://graph.windows.net/",
                "sqlManagementEndpointUrl":
                    "https://management.core.windows.net:8443/",
                "galleryEndpointUrl": "https://gallery.azure.com/",
                "managementEndpointUrl":
                    "https://management.core.windows.net/"
            }
        }
        self.job.source_regions = {
            'cloud_image_name': 'image123',
            'blob_name': 'image123.vhd'
        }
        self.log = Mock()
        self.job._log_callback = self.log

    def test_replicate_ec2_missing_key(self):
        del self.job_config['account']

        with raises(MashReplicateException):
            AzureReplicateJob(self.job_config, self.config)

        self.job_config['account'] = 'acnt1'

    @patch('mash.services.replicate.azure_job.delete_blob')
    @patch('mash.services.replicate.azure_job.delete_image')
    @patch('mash.services.replicate.azure_job.create_json_file')
    @patch('mash.services.replicate.azure_job.copy_blob_to_classic_storage')
    def test_replicate(
        self, mock_copy_blob, mock_create_json_file,
        mock_delete_image, mock_delete_blob
    ):
        mock_delete_blob.side_effect = Exception('Cannot delete image.')
        mock_create_json_file.return_value.__enter__.return_value = \
            '/tmp/file.auth'

        self.job.run_job()

        self.log.info.assert_has_calls([
            call('Copying image for account: acnt1, to classic storage container.'),
            call('Removing ARM image and page blob for account: acnt1.')
        ])
        self.log.error.assert_called_once_with(
            'There was an error copying image blob in acnt1: Cannot delete image.'
        )
        mock_copy_blob.assert_called_once_with(
            '/tmp/file.auth', 'image123.vhd', 'container1', 'rg-1', 'sa1',
            'container2', 'rg-2', 'sa2', is_page_blob=True
        )
        mock_delete_image.assert_called_once_with(
            '/tmp/file.auth', 'rg-1', 'image123'
        )
        mock_delete_blob.assert_called_once_with(
            '/tmp/file.auth', 'image123.vhd', 'container1', 'rg-1', 'sa1',
            is_page_blob=True
        )
        assert self.job.status == FAILED
