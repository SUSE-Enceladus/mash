import pytest

from unittest.mock import call, Mock, patch

from mash.services.test.ec2_job import EC2TestJob
from mash.mash_exceptions import MashTestException


class TestEC2TestJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {
                'us-east-1': {'account': 'test-aws', 'partition': 'aws'}
            },
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cleanup_images': True
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_test_ec2_missing_key(self):
        del self.job_config['test_regions']

        with pytest.raises(MashTestException):
            EC2TestJob(self.job_config, self.config)

    @patch('mash.services.test.ec2_job.cleanup_ec2_image')
    @patch('mash.services.test.ec2_job.os')
    @patch('mash.services.test.ec2_job.create_ssh_key_pair')
    @patch('mash.services.test.ec2_job.random')
    @patch('mash.utils.ec2.EC2Setup')
    @patch('mash.utils.ec2.generate_name')
    @patch('mash.utils.ec2.get_client')
    @patch('mash.utils.ec2.get_key_from_file')
    @patch('mash.utils.ec2.get_vpc_id_from_subnet')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_test_run_test(
        self, mock_test_image, mock_get_vpc_id_from_subnet,
        mock_get_key_from_file, mock_get_client, mock_generate_name,
        mock_ec2_setup, mock_random, mock_create_ssh_key_pair, mock_os,
        mock_cleanup_image
    ):
        client = Mock()
        mock_get_client.return_value = client
        mock_generate_name.return_value = 'random_name'
        mock_get_key_from_file.return_value = 'fakekey'
        mock_random.choice.return_value = 't2.micro'
        mock_get_vpc_id_from_subnet.return_value = 'vpc-123456789'

        ec2_setup = Mock()
        ec2_setup.create_vpc_subnet.return_value = 'subnet-123456789'
        ec2_setup.create_security_group.return_value = 'sg-123456789'
        mock_ec2_setup.return_value = ec2_setup

        mock_test_image.return_value = (
            0,
            {
                'tests': [
                    {
                        "outcome": "passed",
                        "test_index": 0,
                        "name": "test_sles_ec2_metadata.py::test_sles_ec2_metadata[paramiko://10.0.0.10]"
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
                    'instance': 'i-123456789'
                }
            }
        )
        mock_os.path.exists.return_value = False

        job = EC2TestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-aws': {
                'access_key_id': '123',
                'secret_access_key': '321'
            }
        }
        job.status_msg['source_regions'] = {'us-east-1': 'ami-123'}
        job.run_job()

        client.import_key_pair.assert_called_once_with(
            KeyName='random_name', PublicKeyMaterial='fakekey'
        )
        mock_test_image.assert_called_once_with(
            'ec2',
            access_key_id='123',
            availability_domain=None,
            cleanup=True,
            compartment_id=None,
            description=job.description,
            distro='sles',
            image_id='ami-123',
            instance_type='t2.micro',
            log_level=10,
            oci_user_id=None,
            region='us-east-1',
            secret_access_key='321',
            security_group_id='sg-123456789',
            service_account_file=None,
            signing_key_file=None,
            signing_key_fingerprint=None,
            ssh_key_name='random_name',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='ec2-user',
            subnet_id='subnet-123456789',
            tenancy=None,
            tests=['test_stuff'],
            timeout=None,
            enable_secure_boot=False,
            image_project=None,
            log_callback=job._log_callback,
            prefix_name='mash',
            sev_capable=None,
            access_key=None,
            access_secret=None,
            v_switch_id=None,
            use_gvnic=None
        )
        client.delete_key_pair.assert_called_once_with(KeyName='random_name')
        mock_cleanup_image.assert_called_once_with(
            '123',
            '321',
            job._log_callback,
            'us-east-1',
            image_id='ami-123'
        )
        job._log_callback.warning.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job.run_job()
        job._log_callback.warning.assert_has_calls([
            call('Image tests failed in region: us-east-1.')
        ])
        assert 'Tests broken!' in job._log_callback.error.mock_calls[0][1][0]
        assert ec2_setup.clean_up.call_count == 2

        # Failed key cleanup
        client.delete_key_pair.side_effect = Exception('Cannot delete key!')
        job.run_job()

    def test_test_run_test_subnet(self):
        self.job_config['test_regions']['us-east-1']['subnet'] = 'subnet-123456789'
        self.test_test_run_test()

    @patch('mash.services.test.ec2_job.random')
    @patch('mash.services.test.ec2_job.os')
    def test_run_test_arm_skip(self, mock_os, mock_random):
        mock_os.path.exists.return_value = True
        mock_random.choice.return_value = 'a1.large'

        job_config = {
            'id': '2',
            'last_service': 'test',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {
                'cn-east-1': {'account': 'test-aws-cn', 'partition': 'aws-cn'}
            },
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cloud_architecture': 'aarch64'
        }
        job = EC2TestJob(job_config, self.config)
        job._log_callback = Mock()
        job.credentials = {
            'test-aws-cn': {
                'access_key_id': '123',
                'secret_access_key': '321'
            }
        }
        job.status_msg['source_regions'] = {'cn-east-1': 'ami-123'}
        job.run_job()
