import pytest

from unittest.mock import call, Mock, patch

from mash.services.testing.gce_job import GCETestingJob
from mash.mash_exceptions import MashTestingException


class TestGCETestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'gce',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {
                'us-west1': {
                    'account': 'test-gce',
                    'testing_account': 'testingacnt'
                }
            },
            'tests': ['test_stuff'],
            'utctime': 'now',
        }
        self.config = Mock()

    def test_testing_gce_missing_key(self):
        del self.job_config['test_regions']

        with pytest.raises(MashTestingException):
            GCETestingJob(self.job_config, self.config)

    @patch('mash.services.testing.gce_job.random')
    @patch('mash.services.testing.ipa_helper.NamedTemporaryFile')
    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(GCETestingJob, 'send_log')
    def test_testing_run_gce_test(
        self, mock_send_log, mock_test_image, mock_temp_file, mock_random
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
                    'results_file': 'test.results'
                }
            }
        )
        mock_random.choice.return_value = 'n1-standard-1'

        job = GCETestingJob(self.job_config, self.config)
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
        job.source_regions = {'us-west1': 'ami-123'}
        job._run_job()

        mock_test_image.assert_called_once_with(
            'gce',
            access_key_id=None,
            cleanup=True,
            description=job.description,
            distro='sles',
            image_id='ami-123',
            instance_type='n1-standard-1',
            log_level=30,
            region='us-west1',
            secret_access_key=None,
            security_group_id=None,
            service_account_file='/tmp/acnt.file',
            ssh_key_name=None,
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='root',
            subnet_id=None,
            tests=['test_stuff'],
            timeout=None
        )
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job._run_job()
        assert mock_send_log.mock_calls[1] == call(
            'Image tests failed in region: us-west1.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}
