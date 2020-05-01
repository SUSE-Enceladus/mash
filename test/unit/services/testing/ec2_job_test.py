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
            'requesting_user': 'user1',
            'ssh_private_key_file': 'private_ssh_key.file',
            'test_regions': {'us-east-1': {'account': 'test-aws'}},
            'tests': ['test_stuff'],
            'utctime': 'now',
            'cleanup_images': True
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = None

    def test_testing_ec2_missing_key(self):
        del self.job_config['test_regions']

        with pytest.raises(MashTestingException):
            EC2TestingJob(self.job_config, self.config)

    @patch.object(EC2TestingJob, 'cleanup_ec2_image')
    @patch('mash.services.testing.ec2_job.os')
    @patch('mash.services.testing.ec2_job.create_ssh_key_pair')
    @patch('mash.services.testing.ec2_job.random')
    @patch('mash.utils.ec2.EC2Setup')
    @patch('mash.utils.ec2.generate_name')
    @patch('mash.utils.ec2.get_client')
    @patch('mash.utils.ec2.get_key_from_file')
    @patch('mash.utils.ec2.get_vpc_id_from_subnet')
    @patch('mash.services.testing.img_proof_helper.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(
        self, mock_send_log, mock_test_image, mock_get_vpc_id_from_subnet,
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
                'tests': '...',
                'summary': '...',
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results',
                    'instance': 'i-123456789'
                }
            }
        )
        mock_os.path.exists.return_value = False

        job = EC2TestingJob(self.job_config, self.config)
        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')
        job.credentials = {
            'test-aws': {
                'access_key_id': '123',
                'secret_access_key': '321'
            }
        }
        job.source_regions = {'us-east-1': 'ami-123'}
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
            image_project=None
        )
        client.delete_key_pair.assert_called_once_with(KeyName='random_name')
        mock_cleanup_image.assert_called_once_with(
            job.credentials['test-aws'],
            'us-east-1',
            'ami-123'
        )
        mock_send_log.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')
        job.run_job()
        assert mock_send_log.mock_calls[1] == call(
            'Image tests failed in region: us-east-1.', success=False
        )
        assert 'Tests broken!' in mock_send_log.mock_calls[2][1][0]
        assert mock_send_log.mock_calls[2][2] == {'success': False}
        assert ec2_setup.clean_up.call_count == 2

        # Failed key cleanup
        client.delete_key_pair.side_effect = Exception('Cannot delete key!')
        job.run_job()

    def test_testing_run_test_subnet(self):
        self.job_config['test_regions']['us-east-1']['subnet'] = 'subnet-123456789'
        self.test_testing_run_test()

    @patch('mash.services.testing.ec2_job.os')
    @patch('mash.services.testing.ec2_job.random')
    @patch('mash.services.testing.ec2_job.EC2RemoveImage')
    @patch.object(EC2TestingJob, 'send_log')
    def test_cleanup_images(
        self, mock_send_log, mock_rm_img, mock_random, mock_os
    ):
        rm_img = Mock()
        rm_img.remove_images.side_effect = Exception('image not found!')

        mock_rm_img.return_value = rm_img
        mock_random.choice.return_value = 't2.micro'
        mock_os.path.exists.return_value = True

        job = EC2TestingJob(self.job_config, self.config)

        credentials = {
            'access_key_id': '123',
            'secret_access_key': '321'
        }

        job.cleanup_ec2_image(credentials, 'us-east-1', 'ami-123')

        mock_send_log.assert_has_calls([
            call('Cleaning up image: ami-123 in region: us-east-1.'),
            call('Failed to cleanup image: image not found!', success=False)
        ])
        rm_img.set_region.assert_called_once_with('us-east-1')
        rm_img.remove_images.assert_called_once_with()
