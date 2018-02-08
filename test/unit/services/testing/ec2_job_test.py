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

    @patch('mash.services.testing.ec2_job.test_image')
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
        job._run_tests()

        mock_test_image.assert_called_once_with(
            'ec2',
            access_key_id=None,
            desc=job.desc,
            distro='SLES',
            image_id=None,
            instance_type=job.instance_type,
            log_level=30,
            region=None,
            secret_access_key=None,
            ssh_key_name=None,
            ssh_private_key=None,
            ssh_user=None,
            tests=['test_stuff']
        )

        mock_send_log.assert_has_calls(
            [call('Log file: test.log'), call('Results file: test.results')]
        )
