from unittest.mock import call, patch

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

    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(self, mock_send_log, mock_test_image):
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
                'access_key_id': None,
                'secret_access_key': None,
                'ssh_key_name': None,
                'ssh_private_key': None
            }
        }
        job.update_test_regions({'us-east-1': 'ami-123'})
        job._run_tests()

        mock_test_image.assert_called_once_with(
            'EC2',
            access_key_id=None,
            cleanup=True,
            desc=job.description,
            distro='SLES',
            image_id='ami-123',
            instance_type=job.instance_type,
            log_level=30,
            region='us-east-1',
            secret_access_key=None,
            ssh_key_name=None,
            ssh_private_key=None,
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
