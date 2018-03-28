from unittest.mock import call, MagicMock, patch

from mash.services.testing.ec2_job import EC2TestingJob


class TestEC2TestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'ec2',
            'test_regions': {'us-east-1': 'test-aws'},
            'tests': 'test_stuff',
            'utctime': 'now',
        }

    @patch('mash.services.testing.ipa_helper.NamedTemporaryFile')
    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(
        self, mock_send_log, mock_test_image, mock_temp_file
    ):
        tmp_file = MagicMock()
        tmp_file.name = '/tmp/temp.file'
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

        job = EC2TestingJob(**self.job_config)
        job.credentials = {
            'test-aws': {
                'access_key_id': '123',
                'secret_access_key': '321',
                'ssh_key_name': 'my-key',
                'ssh_private_key': 'private-key-123'
            }
        }
        job.source_regions = {'us-east-1': 'ami-123'}
        job._run_tests()

        mock_test_image.assert_called_once_with(
            'ec2',
            cleanup=True,
            access_key_id='123',
            desc=job.description,
            distro='SLES',
            image_id='ami-123',
            instance_type=job.instance_type,
            log_level=30,
            region='us-east-1',
            secret_access_key='321',
            ssh_key_name='my-key',
            ssh_private_key='/tmp/temp.file',
            ssh_user='ec2-user',
            tests=['test_stuff']
        )

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job._run_tests()
        mock_send_log.assert_has_calls(
            [call('Image tests failed in region: us-east-1.', success=False),
             call('Tests broken!', success=False)]
        )
