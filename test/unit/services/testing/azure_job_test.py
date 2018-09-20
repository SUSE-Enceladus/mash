from unittest.mock import call, Mock, patch

from mash.services.testing.azure_job import AzureTestingJob


class TestAzureTestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'azure',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {'East US': 'test-azure'},
            'tests': ['test_stuff'],
            'utctime': 'now',
        }

    @patch('mash.services.testing.ipa_helper.NamedTemporaryFile')
    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(AzureTestingJob, 'send_log')
    def test_testing_run_azure_test(
        self, mock_send_log, mock_test_image, mock_temp_file
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

        job = AzureTestingJob(**self.job_config)
        job.credentials = {
            'test-azure': {
                'fake': '123',
                'credentials': '321'
            }
        }
        job.source_regions = {'East US': 'ami-123'}
        job._run_tests()

        mock_test_image.assert_called_once_with(
            'azure',
            access_key_id=None,
            cleanup=True,
            description=job.description,
            distro='sles',
            image_id='ami-123',
            instance_type=None,
            log_level=30,
            region='East US',
            secret_access_key=None,
            service_account_file='/tmp/acnt.file',
            ssh_key_name=None,
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='azureuser',
            tests=['test_stuff']
        )
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job._run_tests()
        assert mock_send_log.mock_calls[0] == call(
            'Image tests failed in region: East US.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[1][1][0]
        assert mock_send_log.mock_calls[1][2] == {'success': False}
