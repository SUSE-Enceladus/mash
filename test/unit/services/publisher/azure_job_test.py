from pytest import raises
from unittest.mock import call, Mock, patch

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher.azure_job import AzurePublisherJob


class TestAzurePublisherJob(object):
    def setup(self):
        self.job_config = {
            'emails': 'jdoe@fake.com',
            'id': '1',
            'image_description': 'New image for v123',
            'label': 'New Image 123',
            'last_service': 'publisher',
            'requesting_user': 'user1',
            'offer_id': 'sles',
            'cloud': 'azure',
            'publish_regions': [
                {
                    'account': 'acnt1',
                    'destination_resource_group': 'rg-2',
                    'destination_container': 'container2',
                    'destination_storage_account': 'sa2'
                }
            ],
            'publisher_id': 'suse',
            'sku': '123',
            'utctime': 'now',
            'vm_images_key': 'microsoft-azure-corevm.vmImagesPublicAzure',
            'publish_offer': True
        }

        self.config = Mock()
        self.job = AzurePublisherJob(self.job_config, self.config)
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
        self.job.cloud_image_name = 'New Image'

    def test_publish_ec2_missing_key(self):
        del self.job_config['publish_regions']

        with raises(MashPublisherException):
            AzurePublisherJob(self.job_config, self.config)

    @patch(
        'mash.services.publisher.azure_job.wait_on_cloud_partner_operation'
    )
    @patch('mash.services.publisher.azure_job.publish_cloud_partner_offer')
    @patch('mash.services.publisher.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.publisher.azure_job.request_cloud_partner_offer_doc'
    )
    @patch('mash.services.publisher.azure_job.create_json_file')
    @patch.object(AzurePublisherJob, 'send_log')
    @patch.object(AzurePublisherJob, '_get_blob_url')
    def test_publish(
        self, mock_get_blob_url, mock_send_log, mock_create_json_file,
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

        mock_send_log.assert_has_calls([
            call('Publishing image for account: acnt1, using cloud partner API.'),
            call('Updated cloud partner offer doc for account: acnt1.'),
            call('Publishing finished for account: acnt1.')
        ])

    @patch('mash.services.publisher.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.publisher.azure_job.request_cloud_partner_offer_doc'
    )
    @patch('mash.services.publisher.azure_job.create_json_file')
    @patch.object(AzurePublisherJob, 'send_log')
    @patch.object(AzurePublisherJob, '_get_blob_url')
    def test_publish_exception(
        self, mock_get_blob_url, mock_send_log, mock_create_json_file,
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

        mock_send_log.assert_has_calls([
            call('Publishing image for account: acnt1, using cloud partner API.'),
            call(
                'There was an error publishing image in acnt1: Invalid doc!',
                False
            )
        ])

    @patch('mash.services.publisher.azure_job.get_blob_url')
    @patch('mash.services.publisher.azure_job.get_classic_page_blob_service')
    def test_get_blob_url(
        self, mock_get_pbs, mock_get_blob_url
    ):
        pbs = Mock()
        mock_get_pbs.return_value = pbs
        mock_get_blob_url.return_value = 'blob/url'

        url = self.job._get_blob_url(
            'path/to/auth',
            'blob 123',
            'container',
            'group1',
            'account1'
        )

        assert url == 'blob/url'
