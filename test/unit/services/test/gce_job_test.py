import pytest

from unittest.mock import call, Mock, patch, ANY

from mash.services.test.gce_job import GCETestJob
from mash.mash_exceptions import MashTestException
from img_proof.ipa_exceptions import IpaRetryableError


class TestGCETestJob(object):
    def setup_method(self):
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
            'boot_firmware': ['uefi'],
            'guest_os_features': [
                'TDX_CAPABLE',
                'GVNIC',
                'UEFI_COMPATIBLE'
            ]
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = 600
        self.config.get_test_gce_instance_catalog.return_value = [
            {
                'region': 'us-east1-b',
                'test_fallback_regions': [
                    'us-east1-c'
                ],
                'arch': 'X86_64',
                'instance_types': ['n1-standard-1'],
                'boot_types': ['uefi'],
                'shielded_vm': ['securevm_enabled'],
                'nic': ['gvnic_enabled'],
                'confidential_compute': []
            },
            {
                'region': 'us-east1-b',
                'test_fallback_regions': [
                    'us-east1-c'
                ],
                'arch': 'X86_64',
                'instance_types': ['n2d-standard-2'],
                'boot_types': ['uefi'],
                'shielded_vm': ['securevm_enabled'],
                'nic': ['gvnic_enabled'],
                'confidential_compute': [
                    'IntelTdx_enabled'
                ]
            },
            {
                'region': 'us-east1-b',
                'test_fallback_regions': [
                    'us-east1-c'
                ],
                'arch': 'X86_64',
                'instance_types': ['n3d-standard-3'],
                'boot_types': ['uefi'],
                'shielded_vm': ['securevm_enabled'],
                'nic': ['gvnic_enabled'],
                'confidential_compute': [
                    'AmdSev_enabled'
                ]
            },
            {
                'region': 'us-east1-b',
                'test_fallback_regions': [
                    'us-east1-c'
                ],
                'arch': 'X86_64',
                'instance_types': ['n4d-standard-4'],
                'boot_types': ['uefi'],
                'shielded_vm': ['securevm_enabled'],
                'nic': ['gvnic_enabled'],
                'confidential_compute': [
                    'AmdSevSnp_enabled'
                ]
            },

        ]
        self.config.get_gce_instance_feature_additional_tests.return_value = {
            'AmdSev_enabled': ['additional_sev_test_1'],
            'AmdSevSnp_enabled': ['additional_sev_snp_test_1']
        }

    def test_test_gce_missing_key(self):
        """Test class creation with missing key"""
        del self.job_config['account']

        with pytest.raises(MashTestException):
            GCETestJob(self.job_config, self.config)

        self.job_config['account'] = 'test-gce'

    def test_test_run_empty_tests(self):
        """Test run attempt with empty tests"""
        self.job_config['tests'] = []

        test_job = GCETestJob(self.job_config, self.config)
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()
        logger.log.assert_called_once_with(
            20,
            'Skipping test service, no tests provided.',
            extra={'job_id': '1'}
        )
        self.job_config['tests'] = ['test_stuff']

    def test_test_run_empty_test_instance_catalog(self):
        """Test run attempt with empty test_instance catalog"""
        self.job_config['boot_firmware'] = ['bios']
        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        logger = Mock()
        test_job.log_callback = logger
        with pytest.raises(MashTestException) as e:
            test_job.run_job()
        assert 'Configuration error' in str(e)
        self.job_config['boot_firmware'] = ['uefi']

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_intel_tdx(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            (0, successful_test)
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False

        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()

        # test with  tdx, sercure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with TDX and secure_boot without gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=False,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE']
        ) in mock_test_image.mock_calls
        # Test without TDX but with secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=False,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['GVNIC']
        ) in mock_test_image.mock_calls

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_amd_sev(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            (0, successful_test)
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False
        self.job_config['guest_os_features'] = [
            'SEV_CAPABLE',
            'GVNIC',
            'UEFI_COMPATIBLE'
        ]
        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()

        # test with sev, secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff', 'additional_sev_test_1'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'SEV_CAPABLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with SEV and secure_boot without gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff', 'additional_sev_test_1'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=False,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'SEV_CAPABLE']
        ) in mock_test_image.mock_calls
        # Test without SEV but with secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=False,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['GVNIC']
        ) in mock_test_image.mock_calls

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_amd_sev_snp(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            (0, successful_test)
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False
        self.job_config['guest_os_features'] = [
            'SEV_SNP_CAPABLE',
            'GVNIC',
            'UEFI_COMPATIBLE'
        ]
        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()

        # test with sev_snp, secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff', 'additional_sev_snp_test_1'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'SEV_SNP_CAPABLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with sev_snp and secure_boot without gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff', 'additional_sev_snp_test_1'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=False,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'SEV_SNP_CAPABLE']
        ) in mock_test_image.mock_calls
        # Test without sev_snp but with secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=False,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['GVNIC']
        ) in mock_test_image.mock_calls

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_exception(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            Exception('This is an exception')
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False

        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()

        # test with  tdx, sercure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with TDX and secure_boot without gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=False,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE']
        ) in mock_test_image.mock_calls
        # Test without TDX but with secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=False,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['GVNIC']
        ) in mock_test_image.mock_calls
        assert test_job.status == 'failed'
        assert 'This is an exception' in str(test_job.status_msg)

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_retryable_exception(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            IpaRetryableError('Retryable exception'),
            (0, successful_test)
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False

        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()

        # test with  tdx, sercure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with TDX and secure_boot without gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=True,
            use_gvnic=False,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'TDX_CAPABLE']
        ) in mock_test_image.mock_calls
        # Test without TDX but with secure_boot and gvnic
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=True,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['UEFI_COMPATIBLE', 'GVNIC']
        ) in mock_test_image.mock_calls
        # Test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-b',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=['test_stuff'],
            enable_secure_boot=False,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=False,
            use_gvnic=True,
            architecture='X86_64',
            instance_options=['GVNIC']
        ) in mock_test_image.mock_calls
        # Retry of the test with everything disabled
        assert call(
            'gce',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-123',
            instance_type=ANY,
            timeout=600,
            log_level=10,
            region='us-east1-c',
            service_account_file='/tmp/acnt.file',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            tests=ANY,
            enable_secure_boot=ANY,
            image_project=None,
            log_callback=ANY,
            prefix_name='mash',
            sev_capable=ANY,
            use_gvnic=ANY,
            architecture='X86_64',
            instance_options=ANY
        ) in mock_test_image.mock_calls
        assert test_job.status == 'success'
        assert [] == test_job.status_msg['errors']

    @patch('mash.services.test.gce_job.GCERemoveImage')
    @patch('mash.services.test.gce_job.GCERemoveBlob')
    @patch('mash.services.test.gce_job.os')
    @patch('mash.services.test.gce_job.test_image')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    def test_test_run_cleanup_exception(
        self,
        mock_temp_file,
        mock_test_image,
        mock_os,
        mock_blob_remover,
        mock_image_remover
    ):
        """Test run """
        successful_test = {
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
        mock_test_image.side_effect = [
            (0, successful_test),
            (0, successful_test),
            (0, successful_test),
            (0, successful_test)
        ]
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        image_remover = Mock()
        blob_remover = Mock()
        mock_image_remover.return_value = image_remover
        mock_image_remover.return_value.remove_image.side_effect = Exception(
            'remover exception'
        )
        mock_blob_remover.return_value = blob_remover
        mock_os.path.exists.return_value = False

        test_job = GCETestJob(self.job_config, self.config)
        test_job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        test_job.status_msg['cloud_image_name'] = 'ami-123'
        test_job.status_msg['object_name'] = 'ami-123.tar.gz'
        logger = Mock()
        test_job.log_callback = logger
        test_job.run_job()
        assert 'remover exception' in str(test_job.status_msg['errors'])
        assert 'success' in test_job.status
