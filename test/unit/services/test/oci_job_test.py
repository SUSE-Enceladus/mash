import pytest

from unittest.mock import Mock, patch

from mash.services.test.oci_job import OCITestJob
from mash.mash_exceptions import MashTestException
from mash.services.test.config import TestConfig


class TestOCITestJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
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
        self.config = TestConfig(config_file='test/data/mash_config.yaml')

    def test_oci_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestException):
            OCITestJob(self.job_config, self.config)

    @patch.object(OCITestJob, 'cleanup_image')
    @patch('mash.services.test.oci_job.os')
    @patch('mash.services.test.oci_job.create_ssh_key_pair')
    @patch('mash.services.test.oci_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_oci_image_proof(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_cleanup_image
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
                        "name": "test_sles_oci_metadata.py::test_sles_oci_metadata[paramiko://10.0.0.10]"
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
        mock_random.choice.return_value = 'VM.Standard2.1'
        mock_os.path.exists.return_value = False

        job = OCITestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('/var/lib/mash/ssh_key')
        job.credentials = {
            'test-oci': {
                'signing_key': 'test key',
                'fingerprint': 'fake fingerprint'
            }
        }
        job.status_msg['cloud_image_name'] = 'name.qcow2'
        job.status_msg['image_id'] = 'ocid1.image.oc1..'
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
            enable_secure_boot=False,
            image_project=None,
            log_callback=job._log_callback,
            prefix_name='mash',
            sev_capable=None,
            access_key=None,
            access_secret=None,
            v_switch_id=None,
            use_gvnic=None
        )
        job._log_callback.info.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')

        job.run_job()

        job._log_callback.warning.assert_called_once_with(
            'Image tests failed in region: us-phoenix-1.'
        )
        assert 'Tests broken!' in job._log_callback.error.mock_calls[0][1][0]

    @patch('mash.services.test.oci_job.create_ssh_key_pair')
    @patch('mash.services.test.oci_job.ComputeClientCompositeOperations')
    @patch('mash.services.test.oci_job.ComputeClient')
    def test_oci_image_cleanup_after_test(
        self, mock_compute_client, mock_compute_client_composite,
        mock_create_ssh_key_pair
    ):
        job = OCITestJob(self.job_config, self.config)
        job._log_callback = Mock()
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

        job._log_callback.info.assert_called_once_with(
            'Cleaning up image: name.qcow2 in region: us-phoenix-1.'
        )

        # Test failed cleanup
        job._log_callback.info.reset_mock()
        compute_composite_client.delete_image_and_wait_for_state.side_effect = Exception(
            'Image not found!'
        )
        job.cleanup_image(credentials, image_id)

        job._log_callback.info.assert_called_once_with(
            'Cleaning up image: name.qcow2 in region: us-phoenix-1.'
        )
        job._log_callback.warning.assert_called_once_with(
            'Failed to cleanup image: Image not found!'
        )
