from unittest.mock import call, patch

from mash.services.status_levels import FAILED
from mash.services.replication.azure_job import AzureReplicationJob


class TestAzureReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'image_description': 'My image',
            'last_service': 'replication',
            'provider': 'azure',
            'utctime': 'now',
            "replication_source_regions": {
                "westus": {
                    'account': 'acnt1',
                    'source_resource_group': 'rg-1',
                    'source_container': 'container1',
                    'source_storage_account': 'sa1',
                    'destination_resource_group': 'rg-2',
                    'destination_container': 'container2',
                    'destination_storage_account': 'sa2'
                }
            },
            "cleanup_images": True
        }
        self.job = AzureReplicationJob(**self.job_config)

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
        self.job.cloud_image_name = 'image123'

    @patch('mash.services.replication.azure_job.delete_page_blob')
    @patch('mash.services.replication.azure_job.delete_image')
    @patch('mash.services.replication.azure_job.create_auth_file')
    @patch('mash.services.replication.azure_job.copy_blob_to_classic_storage')
    @patch.object(AzureReplicationJob, 'send_log')
    def test_replicate(
        self, mock_send_log, mock_copy_blob, mock_create_auth_file,
        mock_delete_image, mock_delete_page_blob
    ):
        mock_delete_page_blob.side_effect = Exception('Cannot delete image.')
        mock_create_auth_file.return_value.__enter__.return_value = \
            '/tmp/file.auth'

        self.job._replicate()

        mock_send_log.has_calls([
            call('Copying image for account: acnt1, to classic storage container.'),
            call('There was an error copying image blob in acnt1.', False)
        ])
        mock_copy_blob.assert_called_once_with(
            '/tmp/file.auth', 'image123.vhd', 'container1', 'rg-1', 'sa1',
            'container2', 'rg-2', 'sa2'
        )
        mock_delete_image.assert_called_once_with(
            '/tmp/file.auth', 'rg-1', 'image123'
        )
        mock_delete_page_blob.assert_called_once_with(
            '/tmp/file.auth', 'image123.vhd', 'container1', 'rg-1', 'sa1'
        )
        assert self.job.status == FAILED
