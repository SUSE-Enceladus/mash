import pytest

from unittest.mock import call, Mock, patch

from mash.services.testing.ec2_job import EC2TestingJob
from mash.mash_exceptions import MashTestingException


class TestEC2TestingJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'ec2',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {'us-east-1': {'account': 'test-aws'}},
            'tests': ['test_stuff'],
            'utctime': 'now',
        }

    def test_testing_ec2_missing_key(self):
        del self.job_config['test_regions']

        with pytest.raises(MashTestingException):
            EC2TestingJob(self.job_config)

    @patch('mash.services.testing.ec2_job.random')
    @patch('mash.services.testing.ipa_helper.EC2Setup')
    @patch('mash.services.testing.ipa_helper.generate_name')
    @patch('mash.services.testing.ipa_helper.get_client')
    @patch('mash.services.testing.ipa_helper.get_key_from_file')
    @patch('mash.services.testing.ipa_helper.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(
        self, mock_send_log, mock_test_image, mock_get_key_from_file,
        mock_get_client, mock_generate_name, mock_ec2_setup, mock_random
    ):
        client = Mock()
        mock_get_client.return_value = client
        mock_generate_name.return_value = 'random_name'
        mock_get_key_from_file.return_value = 'fakekey'
        mock_random.choice.return_value = 't2.micro'

        ec2_setup = Mock()
        ec2_setup.create_vpc_subnet.return_value = 'subnet-123456789'
        ec2_setup.create_security_group.return_value = 'sg-123456789'
        mock_ec2_setup.return_value = ec2_setup

        mock_test_image.return_value = (
            0,
            {
                'tests': '...',
                'summary': '...',
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results',
                    'instance': 'i-123456789'
                }
            }
        )

        job = EC2TestingJob(self.job_config)
        job.credentials = {
            'test-aws': {
                'access_key_id': '123',
                'secret_access_key': '321'
            }
        }
        job.source_regions = {'us-east-1': 'ami-123'}
        job._run_job()

        client.import_key_pair.assert_called_once_with(
            KeyName='random_name', PublicKeyMaterial='fakekey'
        )
        mock_test_image.assert_called_once_with(
            'ec2',
            access_key_id='123',
            cleanup=True,
            description=job.description,
            distro='sles',
            image_id='ami-123',
            instance_type='t2.micro',
            log_level=30,
            region='us-east-1',
            secret_access_key='321',
            security_group_id='sg-123456789',
            service_account_file=None,
            ssh_key_name='random_name',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='ec2-user',
            subnet_id='subnet-123456789',
            tests=['test_stuff'],
            timeout=None
        )
        client.delete_key_pair.assert_called_once_with(KeyName='random_name')
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job._run_job()
        assert mock_send_log.mock_calls[1] == call(
            'Image tests failed in region: us-east-1.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}
        assert ec2_setup.clean_up.call_count == 2

        # Failed key cleanup
        client.delete_key_pair.side_effect = Exception('Cannot delete key!')
        job._run_job()
