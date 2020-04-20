import pytest

from unittest.mock import call, Mock, patch

from mash.services.testing.oci_job import OCITestingJob
from mash.mash_exceptions import MashTestingException
from mash.services.testing.config import TestingConfig


class TestOCITestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'oci',
            'requesting_user': 'user1',
            'account': 'test-oci',
            'bucket': 'images',
            'region': 'us-phoenix-1',
            'availability_domain': 'Omic:PHX-AD-1',
            'oci_user_id': 'ocid1.user.oc1..',
            'tenancy': 'ocid1.tenancy.oc1..',
            'compartment_id': 'ocid1.compartment.oc1..',
            'operating_system': 'SLES',
            'operating_system_version': '12SP2',
            'tests': ['test_stuff'],
            'utctime': 'now'
        }
        self.config = TestingConfig(config_file='test/data/mash_config.yaml')

    def test_oci_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestingException):
            OCITestingJob(self.job_config, self.config)

    @patch.object(OCITestingJob, 'cleanup_image')
    @patch('mash.services.testing.oci_job.os')
    @patch('mash.services.testing.oci_job.create_ssh_key_pair')
    @patch('mash.services.testing.oci_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.testing.img_proof_helper.test_image')
    @patch.object(OCITestingJob, 'send_log')
    def test_oci_image_proof(
        self, mock_send_log, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_cleanup_image
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
        mock_random.choice.return_value = 'VM.Standard2.1'
        mock_os.path.exists.return_value = False

        job = OCITestingJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('/var/lib/mash/ssh_key')
        job.credentials = {
            'test-oci': {
                'signing_key': 'test key',
                'fingerprint': 'fake fingerprint'
            }
        }
        job.source_regions = {
            'cloud_image_name': 'name.qcow2',
            'image_id': 'ocid1.image.oc1..'
        }
        job.run_job()

        mock_test_image.assert_called_once_with(
            'oci',
            access_key_id=None,
            availability_domain='Omic:PHX-AD-1',
            cleanup=True,
            compartment_id='ocid1.compartment.oc1..',
            description=job.description,
            distro='sles',
            image_id='ocid1.image.oc1..',
            instance_type='VM.Standard2.1',
            log_level=10,
            oci_user_id='ocid1.user.oc1..',
            region='us-phoenix-1',
            secret_access_key=None,
            security_group_id=None,
            service_account_file=None,
            signing_key_file='/tmp/acnt.file',
            signing_key_fingerprint='fake fingerprint',
            ssh_key_name=None,
            ssh_private_key_file='/var/lib/mash/ssh_key',
            ssh_user='opc',
            subnet_id=None,
            tenancy='ocid1.tenancy.oc1..',
            tests=['test_stuff'],
            timeout=600,
            enable_uefi=False,
            enable_secure_boot=False,
            image_project=None
        )
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')

        job.run_job()

        assert mock_send_log.mock_calls[1] == call(
            'Image tests failed in region: us-phoenix-1.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}

    @patch('mash.services.testing.oci_job.create_ssh_key_pair')
    @patch('mash.services.testing.oci_job.ComputeClientCompositeOperations')
    @patch('mash.services.testing.oci_job.ComputeClient')
    @patch.object(OCITestingJob, 'send_log')
    def test_oci_image_cleanup_after_test(
        self, mock_send_log, mock_compute_client, mock_compute_client_composite,
        mock_create_ssh_key_pair
    ):
        job = OCITestingJob(self.job_config, self.config)
        job.cloud_image_name = 'name.qcow2'

        compute_client = Mock()
        mock_compute_client.return_value = compute_client

        compute_composite_client = Mock()
        mock_compute_client_composite.return_value = compute_composite_client

        credentials = {
            'signing_key': 'test key',
            'fingerprint': 'fake fingerprint'
        }
        image_id = 'ocid1.image.oc1..'

        job.cleanup_image(credentials, image_id)

        mock_send_log.assert_called_once_with(
            'Cleaning up image: name.qcow2 in region: us-phoenix-1.'
        )

        # Test failed cleanup
        mock_send_log.reset_mock()
        compute_composite_client.delete_image_and_wait_for_state.side_effect = Exception(
            'Image not found!'
        )
        job.cleanup_image(credentials, image_id)

        mock_send_log.assert_has_calls([
            call('Cleaning up image: name.qcow2 in region: us-phoenix-1.'),
            call(
                'Failed to cleanup image: Image not found!',
                success=False
            )
        ])
