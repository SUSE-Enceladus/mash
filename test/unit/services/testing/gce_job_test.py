import pytest

from unittest.mock import call, Mock, patch

from mash.services.testing.gce_job import GCETestingJob
from mash.mash_exceptions import MashTestingException
from img_proof.ipa_exceptions import IpaRetryableError


class TestGCETestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'region': 'us-west1-c',
            'account': 'test-gce',
            'testing_account': 'testingacnt',
            'bucket': 'bucket',
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cleanup_images': True
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_testing_gce_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestingException):
            GCETestingJob(self.job_config, self.config)

        self.job_config['account'] = 'test-gce'

    @patch('mash.services.testing.gce_job.get_region_list')
    @patch('mash.services.testing.gce_job.cleanup_gce_image')
    @patch('mash.services.testing.gce_job.os')
    @patch('mash.services.testing.gce_job.create_ssh_key_pair')
    @patch('mash.services.testing.gce_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.testing.img_proof_helper.test_image')
    @patch.object(GCETestingJob, 'send_log')
    def test_testing_run_gce_test(
        self, mock_send_log, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_cleanup_image, mock_get_region_list
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
        mock_random.choice.return_value = 'n1-standard-1'
        mock_os.path.exists.return_value = False
        mock_get_region_list.return_value = set('us-west1-c')

        if 'test_fallback_regions' in self.job_config:
            mock_test_image.side_effect = IpaRetryableError('quota exceeded')

        job = GCETestingJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testingacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.source_regions = {'cloud_image_name': 'ami-123'}
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
                log_level=30,
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
                timeout=None
            )
        ])
        mock_send_log.reset_mock()
        mock_cleanup_image.side_effect = Exception('Unable to cleanup image!')

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job.run_job()
        assert 'Image tests failed' in mock_send_log.mock_calls[1][1][0]
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}

    @patch('mash.services.testing.gce_job.get_region_list')
    @patch('mash.services.testing.gce_job.cleanup_gce_image')
    @patch('mash.services.testing.gce_job.os')
    @patch('mash.services.testing.gce_job.create_ssh_key_pair')
    @patch('mash.services.testing.gce_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.testing.img_proof_helper.test_image')
    @patch.object(GCETestingJob, 'send_log')
    def test_testing_run_default_fallback(
            self, mock_send_log, mock_test_image, mock_temp_file, mock_random,
            mock_create_ssh_key_pair, mock_os, mock_cleanup_image, mock_get_region_list
    ):
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        mock_random.choice.side_effect = ['n1-standard-1', 'us-east1-c']
        mock_os.path.exists.return_value = False
        mock_get_region_list.return_value = set(['us-west1-c', 'us-east1-c'])
        mock_test_image.side_effect = IpaRetryableError('quota exceeded')

        job = GCETestingJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-gce': {
                'fake': '123',
                'credentials': '321'
            },
            'testingacnt': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.source_regions = {'cloud_image_name': 'ami-123'}
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
                log_level=30,
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
                timeout=None
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
                log_level=30,
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
                timeout=None
            )
        ])

    def test_testing_run_gce_test_no_fallback_region(self):
        self.job_config['test_fallback_regions'] = []
        self.test_testing_run_gce_test()

    def test_testing_run_gce_test_explicit_fallback_region(self):
        self.job_config['test_fallback_regions'] = ['us-west1-c']
        self.test_testing_run_gce_test()
