from pytest import raises
from unittest.mock import call, Mock, patch, MagicMock

from mash.mash_exceptions import MashPublishException
from mash.services.publish.azure_job import AzurePublishJob


class TestAzurePublishJob(object):
    def setup(self):
        self.job_config = {
            'emails': 'jdoe@fake.com',
            'id': '1',
            'image_description': 'New image for v123',
            'label': 'New Image 123',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'offer_id': 'sles',
            'cloud': 'azure',
            'account': 'acnt1',
            'resource_group': 'rg-2',
            'container': 'container2',
            'storage_account': 'sa2',
            'region': 'East US',
            'publisher_id': 'suse',
            'sku': '123',
            'utctime': 'now',
            'vm_images_key': 'microsoft-azure-corevm.vmImagesPublicAzure',
            'publish_offer': True
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

    @patch(
        'mash.services.publish.azure_job.wait_on_cloud_partner_operation'
    )
    @patch('mash.services.publish.azure_job.publish_cloud_partner_offer')
    @patch('mash.services.publish.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.publish.azure_job.request_cloud_partner_offer_doc'
    )
    @patch('mash.services.publish.azure_job.create_json_file')
    @patch.object(AzurePublishJob, '_get_blob_url')
    def test_publish(
        self, mock_get_blob_url, mock_create_json_file,
        mock_request_doc, mock_put_doc, mock_publish_offer,
        mock_wait_on_operation
    ):
        self.job.vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'
        mock_get_blob_url.return_value = 'blob/url/.vhd'
        mock_create_json_file.return_value.__enter__.return_value = \
            '/tmp/file.auth'

        mock_request_doc.return_value = {
            'definition': {
                'plans': [
                    {'planId': '123'}
                ]
            }
        }

        mock_publish_offer.return_value = '/api/operation/url'

        self.job.run_job()

        self.log.info.assert_has_calls([
            call('Publishing image for account: acnt1, using cloud partner API.'),
            call('Updated cloud partner offer doc for account: acnt1.'),
            call('Publishing finished for account: acnt1.')
        ])

    @patch('mash.services.publish.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.publish.azure_job.request_cloud_partner_offer_doc'
    )
    @patch('mash.services.publish.azure_job.create_json_file')
    @patch.object(AzurePublishJob, '_get_blob_url')
    def test_publish_exception(
        self, mock_get_blob_url, mock_create_json_file,
        mock_request_doc, mock_put_doc
    ):
        self.job.vm_images_key = None
        mock_get_blob_url.return_value = 'blob/url/.vhd'
        mock_create_json_file.return_value.__enter__.return_value = \
            '/tmp/file.auth'

        mock_request_doc.return_value = {
            'definition': {
                'plans': [
                    {'planId': '123'}
                ]
            }
        }
        mock_put_doc.side_effect = Exception('Invalid doc!')

        self.job.run_job()

        self.log.info.assert_called_once_with(
            'Publishing image for account: acnt1, using cloud partner API.'
        )
        self.log.error.assert_called_once_with(
            'There was an error publishing image in acnt1: Invalid doc!'
        )

    @patch('mash.services.publish.azure_job.get_blob_url')
    @patch('mash.services.publish.azure_job.get_classic_blob_service')
    def test_get_blob_url(
        self, mock_get_bs, mock_get_blob_url
    ):
        bs = Mock()
        mock_get_bs.return_value = bs
        mock_get_blob_url.return_value = 'blob/url'

        url = self.job._get_blob_url(
            'path/to/auth',
            'blob 123',
            'container',
            'group1',
            'account1'
        )

        assert url == 'blob/url'
