import pytest

from unittest.mock import call, Mock, patch

from mash.services.test.azure_sig_job import AzureSIGTestJob
from mash.mash_exceptions import MashTestException


class TestAzureSIGTestJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
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
            'gallery_name': 'gallery1'
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_test_azure_sig_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestException):
            AzureSIGTestJob(self.job_config, self.config)

    @patch('mash.services.test.azure_sig_job.AzureImage')
    @patch('mash.services.test.azure_sig_job.os')
    @patch('mash.services.test.azure_sig_job.create_ssh_key_pair')
    @patch('mash.services.test.azure_sig_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_run_azure_sig_test(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_azure_image
    ):
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        mock_test_image.return_value = (
            0,
            {
                'tests': [
                    {
                        "outcome": "passed",
                        "test_index": 0,
                        "name": "test_sles_azure_metadata.py::test_sles_azure_metadata[paramiko://10.0.0.10]"
                    }
                ],
                'summary': {
                    "duration": 2.839970827102661,
                    "passed": 1,
                    "num_tests": 1
                },
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results',
                    'instance': 'instance-abc'
                }
            }
        )
        mock_random.choice.return_value = 'Standard_A0'
        mock_os.path.exists.return_value = False

        azure_image = Mock()
        mock_azure_image.return_value = azure_image

        job = AzureSIGTestJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-azure': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.status_msg['image_version'] = '2022.02.02'
        job.status_msg['blob_name'] = 'name.vhd'
        job._log_callback = Mock()
        job.status_msg['images'] = ['image_123_gen2']
        job.run_job()

        mock_test_image.assert_called_once_with(
            'azure',
            access_key_id=None,
            availability_domain=None,
            cleanup=True,
            compartment_id=None,
            description=job.description,
            distro='sles',
            image_id='image_123_gen2',
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
            enable_secure_boot=True,
            image_project=None,
            log_callback=job._log_callback,
            prefix_name='mash',
            sev_capable=None,
            access_key=None,
            access_secret=None,
            v_switch_id=None,
            use_gvnic=None,
            gallery_name='gallery1',
            gallery_resource_group='srg',
            image_version='2022.02.02'
        )
        job._log_callback.info.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        azure_image.delete_storage_blob.side_effect = Exception(
            'Cleanup blob failed!'
        )

        job.run_job()

        assert 'Tests broken!' in job._log_callback.error.mock_calls[0][1][0]
        assert azure_image.delete_gallery_image_version.call_count == 1
        assert azure_image.delete_storage_blob.call_count == 1

        # Failed cleanup image
        azure_image.delete_gallery_image_version.side_effect = Exception(
            'Cleanup image failed!'
        )
        azure_image.delete_storage_blob.side_effect = None

        job.run_job()

        job._log_callback.warning.assert_has_calls([
            call('Image tests failed in region: East US.'),
            call('Failed to cleanup image page blob: Cleanup blob failed!'),
            call('Image tests failed in region: East US.'),
            call(
                'Failed to clean up image version: 2022.02.02 of '
                'image: image_123_gen2 in gallery: gallery1. '
                'Cleanup image failed!.'
            )
        ])
