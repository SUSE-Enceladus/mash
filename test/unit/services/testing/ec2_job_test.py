from unittest.mock import call, Mock, patch

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

    @patch('mash.services.testing.ipa_helper.generate_public_ssh_key')
    @patch('mash.services.testing.ipa_helper.get_client')
    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(
        self, mock_send_log, mock_test_image, mock_get_client,
        mock_generate_ssh_key
    ):
        client = Mock()
        client.describe_key_pairs.side_effect = Exception('Key not found.')
        mock_get_client.return_value = client

        mock_generate_ssh_key.return_value = 'fakekey'

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
                'ssh_private_key': 'my-key.file'
            }
        }
        job.update_test_regions({'us-east-1': 'ami-123'})
        job._run_tests()

        client.describe_key_pairs.assert_called_once_with(
            KeyNames=['my-key']
        )
        client.import_key_pair.assert_called_once_with(
            KeyName='my-key', PublicKeyMaterial='fakekey'
        )
        mock_test_image.assert_called_once_with(
            'EC2',
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
            ssh_private_key='my-key.file',
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
