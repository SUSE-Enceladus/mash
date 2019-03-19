from unittest.mock import call, patch

from mash.services.deprecation.azure_job import AzureDeprecationJob


class TestAzureDeprecationJob(object):
    def setup(self):
        self.job_config = {
            'emails': 'jdoe@fake.com',
            'id': '1',
            'last_service': 'publisher',
            'offer_id': 'sles',
            'cloud': 'azure',
            'deprecation_regions': ['acnt1'],
            'old_cloud_image_name': 'old_image_20190909',
            'publisher_id': 'suse',
            'sku': '123',
            'utctime': 'now',
            'vm_images_key': 'microsoft-azure-corevm.vmImagesPublicAzure'
        }

        self.job = AzureDeprecationJob(**self.job_config)
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

    @patch('mash.services.deprecation.azure_job.deprecate_image_in_offer_doc')
    @patch('mash.services.deprecation.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.deprecation.azure_job.request_cloud_partner_offer_doc'
    )
    @patch.object(AzureDeprecationJob, 'send_log')
    def test_deprecate(
        self, mock_send_log, mock_request_doc, mock_put_doc,
        mock_deprecate_image
    ):
        self.job.vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'

        mock_request_doc.return_value = {
            'definition': {
                'plans': [
                    {
                        'planId': '123',
                        self.job.vm_images_key: {
                            '2018.09.09': {
                                'label': 'New Image 20180909'
                            }
                        }
                    }
                ]
            }
        }

        self.job._deprecate()

        mock_send_log.assert_has_calls([
            call(
                'Deprecating image for account: '
                'acnt1, using cloud partner API.'
            ),
            call('Deprecation finished for account: acnt1.')
        ])

    @patch('mash.services.deprecation.azure_job.deprecate_image_in_offer_doc')
    @patch('mash.services.deprecation.azure_job.put_cloud_partner_offer_doc')
    @patch(
        'mash.services.deprecation.azure_job.request_cloud_partner_offer_doc'
    )
    @patch.object(AzureDeprecationJob, 'send_log')
    def test_deprecate_exception(
        self, mock_send_log, mock_request_doc, mock_put_doc,
        mock_deprecate_image
    ):
        self.job.vm_images_key = None

        mock_request_doc.return_value = {
            'definition': {
                'plans': [
                    {
                        'planId': '123',
                        self.job.vm_images_key: {
                            '2018.09.09': {
                                'label': 'New Image 20180909'
                            }
                        }
                    }
                ]
            }
        }

        mock_put_doc.side_effect = Exception('Invalid doc!')
        self.job.old_cloud_image_name = 'image_123'

        self.job._deprecate()

        mock_send_log.assert_has_calls([
            call(
                'Deprecating image for account: '
                'acnt1, using cloud partner API.'
            ),
            call(
                'There was an error deprecating image in acnt1: Invalid doc!',
                False
            )
        ])
