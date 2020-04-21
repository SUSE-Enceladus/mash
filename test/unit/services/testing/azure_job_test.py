import pytest

from unittest.mock import call, Mock, patch

from mash.services.testing.azure_job import AzureTestingJob
from mash.mash_exceptions import MashTestingException


class TestAzureTestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'azure',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'account': 'test-azure',
            'resource_group': 'srg',
            'container': 'sc',
            'storage_account': 'ssa',
            'region': 'East US',
            'tests': ['test_stuff'],
            'utctime': 'now',
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_testing_azure_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestingException):
            AzureTestingJob(self.job_config, self.config)

    @patch('mash.services.testing.azure_job.delete_image')
    @patch('mash.services.testing.azure_job.delete_page_blob')
    @patch('mash.services.testing.azure_job.os')
    @patch('mash.services.testing.azure_job.create_ssh_key_pair')
    @patch('mash.services.testing.azure_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.testing.img_proof_helper.test_image')
    @patch.object(AzureTestingJob, 'send_log')
    def test_testing_run_azure_test(
        self, mock_send_log, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_delete_blob, mock_delete_image
    ):
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        mock_test_image.return_value = (
            0,
            {
                'tests': '...',
                'summary': '...',
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results',
                    'instance': 'instance-abc'
                }
            }
        )
        mock_random.choice.return_value = 'Standard_A0'
        mock_os.path.exists.return_value = False

        job = AzureTestingJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-azure': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.source_regions = {
            'cloud_image_name': 'name',
            'blob_name': 'name.vhd'
        }
        job.cloud_image_name = 'test_image'
        job.run_job()

        mock_test_image.assert_called_once_with(
            'azure',
            access_key_id=None,
            availability_domain=None,
            cleanup=True,
            compartment_id=None,
            description=job.description,
            distro='sles',
            image_id='name',
            instance_type='Standard_A0',
            log_level=10,
            oci_user_id=None,
            region='East US',
            secret_access_key=None,
            security_group_id=None,
            service_account_file='/tmp/acnt.file',
            signing_key_file=None,
            signing_key_fingerprint=None,
            ssh_key_name=None,
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='azureuser',
            subnet_id=None,
            tenancy=None,
            tests=['test_stuff'],
            timeout=None,
            enable_uefi=False,
            enable_secure_boot=False,
            image_project=None
        )
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        mock_delete_blob.side_effect = Exception('Cleanup blob failed!')

        job.run_job()

        assert mock_send_log.mock_calls[1] == call(
            'Image tests failed in region: East US.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}
        assert mock_delete_image.call_count == 1
        assert mock_delete_blob.call_count == 1
