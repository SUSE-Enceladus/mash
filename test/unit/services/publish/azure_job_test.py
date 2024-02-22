from pytest import raises
from unittest.mock import call, Mock, patch, MagicMock

from mash.mash_exceptions import MashPublishException
from mash.services.publish.azure_job import AzurePublishJob


class TestAzurePublishJob(object):
    def setup(self):
        self.job_config = {
            'emails': 'jdoe@fake.com',
            'id': '1',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'offer_id': 'sles',
            'cloud': 'azure',
            'account': 'acnt1',
            'resource_group': 'rg-2',
            'container': 'container2',
            'storage_account': 'sa2',
            'region': 'East US',
            'sku': '123',
            'utctime': 'now',
        }

        self.config = Mock()
        self.job = AzurePublishJob(self.job_config, self.config)
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
        self.job.status_msg['cloud_image_name'] = 'New Image'
        self.job.status_msg['blob_name'] = 'New Image.vhd'
        self.log = MagicMock()
        self.job._log_callback = self.log

    def test_publish_ec2_missing_key(self):
        del self.job_config['account']

        with raises(MashPublishException):
            AzurePublishJob(self.job_config, self.config)

    @patch('mash.services.publish.azure_job.AzureImage')
    def test_publish(self, mock_azure_image):
        azure_image = MagicMock()
        mock_azure_image.return_value = azure_image

        self.job.run_job()

        self.log.info.assert_has_calls([
            call(
                'Adding image to offer for account: acnt1, '
                'using cloud partner API.'
            ),
            call('Updated cloud partner offer doc for account: acnt1.'),
        ])

    @patch('mash.services.publish.azure_job.AzureImage')
    def test_publish_exception(self, mock_azure_image):
        azure_image = MagicMock()
        mock_azure_image.return_value = azure_image
        azure_image.add_image_to_offer.side_effect = Exception('Invalid doc!')

        self.job.run_job()

        self.log.info.assert_called_once_with(
            'Adding image to offer for account: '
            'acnt1, using cloud partner API.'
        )
        self.log.error.assert_called_once_with(
            'There was an error adding image to offer in acnt1: Invalid doc!'
        )
