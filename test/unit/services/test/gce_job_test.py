import pytest

from unittest.mock import call, Mock, patch

from mash.services.test.gce_job import GCETestJob
from mash.mash_exceptions import MashTestException
from img_proof.ipa_exceptions import IpaRetryableError


class TestGCETestJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'region': 'us-west1-c',
            'account': 'test-gce',
            'testing_account': 'testacnt',
            'bucket': 'bucket',
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cleanup_images': True,
            'boot_firmware': ['uefi']
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_test_gce_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestException):
            GCETestJob(self.job_config, self.config)

        self.job_config['account'] = 'test-gce'

    @patch('mash.services.test.gce_job.get_gce_compute_driver')
    @patch('mash.services.test.gce_job.get_gce_storage_driver')
    @patch('mash.services.test.gce_job.delete_gce_image')
    @patch('mash.services.test.gce_job.delete_image_tarball')
    @patch('mash.services.test.gce_job.get_region_list')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.create_ssh_key_pair')
    @patch('mash.services.test.gce_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_test_run_gce_test(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_get_region_list,
        mock_delete_image_tarball, mock_delete_image, mock_get_storage_driver,
        mock_get_compute_driver
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
                        "name": "test_sles_gce_metadata.py::test_sles_gce_metadata[paramiko://10.0.0.10]"
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
        mock_random.choice.return_value = 'n1-standard-1'
        mock_os.path.exists.return_value = False
        mock_get_region_list.return_value = set('us-west1-c')

        if 'test_fallback_regions' in self.job_config:
            mock_test_image.side_effect = IpaRetryableError('quota exceeded')

        job = GCETestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.status_msg['cloud_image_name'] = 'ami-123'
        job.status_msg['object_name'] = 'ami-123.tar.gz'
        job.run_job()

        mock_test_image.assert_has_calls([
            call(
                'gce',
                access_key_id=None,
                availability_domain=None,
                cleanup=True,
                compartment_id=None,
                description=job.description,
                distro='sles',
                image_id='ami-123',
                instance_type='n1-standard-1',
                log_level=10,
                oci_user_id=None,
                region='us-west1-c',
                secret_access_key=None,
                security_group_id=None,
                service_account_file='/tmp/acnt.file',
                signing_key_file=None,
                signing_key_fingerprint=None,
                ssh_key_name=None,
                ssh_private_key_file='private_ssh_key.file',
                ssh_user='root',
                subnet_id=None,
                tenancy=None,
                tests=['test_stuff'],
                timeout=None,
                enable_secure_boot=True,
                image_project=None,
                log_callback=job._log_callback,
                prefix_name='mash',
                sev_capable=False,
                access_key=None,
                access_secret=None,
                v_switch_id=None,
                use_gvnic=False
            )
        ])
        job._log_callback.warning.reset_mock()
        job._log_callback.error.reset_mock()
        mock_delete_image_tarball.side_effect = Exception('Unable to cleanup image!')

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job.run_job()
        job._log_callback.warning.assert_has_calls([
            call('Image tests failed in region: us-west1-c.'),
            call('Failed to cleanup image: Unable to cleanup image!')
        ])
        assert 'Tests broken!' in job._log_callback.error.mock_calls[0][1][0]

    @patch('mash.services.test.gce_job.get_gce_compute_driver')
    @patch('mash.services.test.gce_job.get_gce_storage_driver')
    @patch('mash.services.test.gce_job.delete_gce_image')
    @patch('mash.services.test.gce_job.delete_image_tarball')
    @patch('mash.services.test.gce_job.get_region_list')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.create_ssh_key_pair')
    @patch('mash.services.test.gce_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_test_run_default_fallback(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_get_region_list,
        mock_delete_image_tarball, mock_delete_image, mock_get_storage_driver,
        mock_get_compute_driver
    ):
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        mock_random.choice.side_effect = ['n1-standard-1', 'us-east1-c']
        mock_os.path.exists.return_value = False
        mock_get_region_list.return_value = set(['us-west1-c', 'us-east1-c'])
        mock_test_image.side_effect = IpaRetryableError('quota exceeded')

        job = GCETestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.status_msg['cloud_image_name'] = 'ami-123'
        job.status_msg['object_name'] = 'ami-123.tar.gz'
        job.run_job()

        mock_test_image.assert_has_calls([
            call(
                'gce',
                access_key_id=None,
                availability_domain=None,
                cleanup=True,
                compartment_id=None,
                description=job.description,
                distro='sles',
                image_id='ami-123',
                instance_type='n1-standard-1',
                log_level=10,
                oci_user_id=None,
                region='us-west1-c',
                secret_access_key=None,
                security_group_id=None,
                service_account_file='/tmp/acnt.file',
                signing_key_file=None,
                signing_key_fingerprint=None,
                ssh_key_name=None,
                ssh_private_key_file='private_ssh_key.file',
                ssh_user='root',
                subnet_id=None,
                tenancy=None,
                tests=['test_stuff'],
                timeout=None,
                enable_secure_boot=True,
                image_project=None,
                log_callback=job._log_callback,
                prefix_name='mash',
                sev_capable=False,
                access_key=None,
                access_secret=None,
                v_switch_id=None,
                use_gvnic=False
            ),
            call(
                'gce',
                access_key_id=None,
                availability_domain=None,
                cleanup=True,
                compartment_id=None,
                description=job.description,
                distro='sles',
                image_id='ami-123',
                instance_type='n1-standard-1',
                log_level=10,
                oci_user_id=None,
                region='us-east1-c',
                secret_access_key=None,
                security_group_id=None,
                service_account_file='/tmp/acnt.file',
                signing_key_file=None,
                signing_key_fingerprint=None,
                ssh_key_name=None,
                ssh_private_key_file='private_ssh_key.file',
                ssh_user='root',
                subnet_id=None,
                tenancy=None,
                tests=['test_stuff'],
                timeout=None,
                enable_secure_boot=True,
                image_project=None,
                log_callback=job._log_callback,
                prefix_name='mash',
                sev_capable=False,
                access_key=None,
                access_secret=None,
                v_switch_id=None,
                use_gvnic=False
            )
        ])

    def test_test_run_gce_test_no_fallback_region(self):
        self.job_config['test_fallback_regions'] = []
        self.test_test_run_gce_test()

    def test_test_run_gce_test_explicit_fallback_region(self):
        self.job_config['test_fallback_regions'] = ['us-west1-c']
        self.test_test_run_gce_test()

    @patch('mash.services.test.gce_job.os')
    def test_test_gce_sev_capable(self, mock_os):
        mock_os.path.exists.return_value = True

        self.job_config['guest_os_features'] = ['SEV_CAPABLE']

        job = GCETestJob(self.job_config, self.config)
        assert job.sev_capable
        assert job.region == 'us-east1-b'
        assert job.instance_type == 'n2d-standard-2'
        assert 'us-central1-a' in job.test_fallback_regions
        assert 'us-west1-b' in job.test_fallback_regions

        self.job_config['guest_os_features'] = None

    @patch('mash.services.test.gce_job.get_gce_compute_driver')
    @patch('mash.services.test.gce_job.get_gce_storage_driver')
    @patch('mash.services.test.gce_job.delete_gce_image')
    @patch('mash.services.test.gce_job.delete_image_tarball')
    @patch('mash.services.test.gce_job.get_region_list')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.create_ssh_key_pair')
    @patch('mash.services.test.gce_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_run_gce_gvnic(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_get_region_list,
        mock_delete_image_tarball, mock_delete_image, mock_get_storage_driver,
        mock_get_compute_driver
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
                        "name": "test_sles_gce_metadata.py::test_sles_gce_metadata[paramiko://10.0.0.10]"
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
        mock_random.choice.side_effect = ['uefi', 'n1-standard-1']
        mock_os.path.exists.return_value = False
        mock_get_region_list.return_value = set('us-west1-c')
        self.job_config['guest_os_features'] = ['GVNIC']

        if 'test_fallback_regions' in self.job_config:
            mock_test_image.side_effect = IpaRetryableError('quota exceeded')

        job = GCETestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.status_msg['cloud_image_name'] = 'ami-123'
        job.status_msg['object_name'] = 'ami-123.tar.gz'
        job.run_job()

        mock_test_image.assert_has_calls([
            call(
                'gce',
                access_key_id=None,
                availability_domain=None,
                cleanup=True,
                compartment_id=None,
                description=job.description,
                distro='sles',
                image_id='ami-123',
                instance_type='n1-standard-1',
                log_level=10,
                oci_user_id=None,
                region='us-west1-c',
                secret_access_key=None,
                security_group_id=None,
                service_account_file='/tmp/acnt.file',
                signing_key_file=None,
                signing_key_fingerprint=None,
                ssh_key_name=None,
                ssh_private_key_file='private_ssh_key.file',
                ssh_user='root',
                subnet_id=None,
                tenancy=None,
                tests=['test_stuff'],
                timeout=None,
                enable_secure_boot=True,
                image_project=None,
                log_callback=job._log_callback,
                prefix_name='mash',
                sev_capable=False,
                access_key=None,
                access_secret=None,
                v_switch_id=None,
                use_gvnic=True
            )
        ])
