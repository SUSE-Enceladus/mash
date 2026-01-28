import pytest

from unittest.mock import (
    call,
    Mock,
    patch,
    ANY
)

from mash.services.test.ec2_job import EC2TestJob
from mash.mash_exceptions import MashTestException


class TestEC2TestJob(object):
    def setup_method(self):
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
            'cleanup_images': True,
            'cloud_architecture': 'x86_64',
            'boot_firmware': ['uefi-preferred'],
            'cpu_options': {
                'AmdSevSnp': 'enabled'
            }
        }
        self.config = Mock()
        self.config.get_ssh_private_key_file.return_value = \
            'private_ssh_key.file'
        self.config.get_img_proof_timeout.return_value = 600
        self.config.get_test_ec2_instance_catalog.return_value = [
            {
                "region": "us-east-2",
                "arch": "x86_64",
                "instance_types": [
                    "m6a.large"
                ],
                "boot_types": [
                    "uefi-preferred",
                    "uefi"
                ],
                "cpu_options": [],
                "partition": "aws"
            },
            {
                "region": "us-east-2",
                "arch": "x86_64",
                "instance_types": [
                    "m6a.large"
                ],
                "boot_types": [
                    "uefi-preferred",
                    "uefi"
                ],
                "cpu_options": [
                    "AmdSevSnp_enabled"
                ],
                "partition": "aws"
            },
            {
                "region": "us-east-1",
                "arch": "aarch64",
                "instance_types": [
                    "t4g.small",
                    "m6g.medium"
                ],
                "boot_types": [],
                "cpu_options": [],
                "partition": "aws"
            }
        ]
        self.config.get_ec2_instance_feature_additional_tests.return_value = {
            'AmdSevSnp_enabled': ['test_sev_snp']
        }

    def test_test_ec2_missing_key(self):
        del self.job_config['test_regions']

        with pytest.raises(MashTestException):
            EC2TestJob(self.job_config, self.config)

    @patch('mash.services.test.ec2_job.cleanup_ec2_image')
    @patch('mash.services.test.ec2_job.os')
    # @patch('mash.services.test.ec2_job.random')
    @patch('mash.utils.ec2.EC2Setup')
    @patch('mash.utils.ec2.generate_name')
    @patch('mash.utils.ec2.get_client')
    @patch('mash.utils.ec2.get_key_from_file')
    @patch('mash.utils.ec2.get_vpc_id_from_subnet')
    @patch('mash.services.test.ec2_job.test_image')
    @patch('mash.services.test.ec2_job.create_ssh_key_pair')
    def test_test_run_test(
        self,
        mock_create_ssh_key_pair,
        mock_test_image,
        mock_get_vpc_id_from_subnet,
        mock_get_key_from_file,
        mock_get_client,
        mock_generate_name,
        mock_ec2_setup,
        mock_os,
        mock_cleanup_image
    ):
        client = Mock()
        mock_get_client.return_value = client
        mock_generate_name.return_value = 'random_name'
        mock_get_key_from_file.return_value = 'fakekey'
        #     mock_random.choice.return_value = 't2.micro'
        mock_get_vpc_id_from_subnet.return_value = 'vpc-123456789'

        ec2_setup = Mock()
        ec2_setup.create_vpc_subnet.return_value = 'subnet-1111111'
        ec2_setup.create_security_group.return_value = 'sg-11111111'
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
                    'instance': 'i-11111111'
                }
            }
        )
        mock_os.path.exists.return_value = False

        job = EC2TestJob(self.job_config, self.config)
        job._log_callback = Mock()

        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')

        job.test_regions = {
            'us-east-1': {
                'partition': 'aws',
                'account': 'us-east-1-test-account',
                'subnet': 'subnet_east_1'
            },
            'us-east-2': {
                'partition': 'aws',
                'account': 'us-east-2-test-account',
                'subnet': 'subnet_east_2'
            },
        }
        job.credentials = {
            'us-east-1-test-account': {
                'access_key_id': '111_',
                'secret_access_key': '_111'
            },
            'us-east-2-test-account': {
                'access_key_id': '222_',
                'secret_access_key': '_222'
            }
        }
        job.status_msg['source_regions'] = {'us-east-1': 'ami-123'}
        job.status_msg['test_replicated_regions'] = {'us-east-2': 'ami-321'}
        job.run_job()

        client.import_key_pair.asser_has_calls([
            call(KeyName='random_name', PublicKeyMaterial='fakekey'),
            call(KeyName='random_name', PublicKeyMaterial='fakekey')
        ])
        client.get_waiter.assert_has_calls([
            call('instance_terminated'),
            call().wait(InstanceIds=['i-11111111']),
            call('instance_terminated'),
            call().wait(InstanceIds=['i-11111111'])
        ])
        client.delete_key_pair.assert_has_calls([
            call(KeyName='random_name')
        ])

        mock_call_1 = call(
            'ec2',
            access_key_id='222_',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-321',
            instance_type='m6a.large',
            timeout=600,
            log_level=10,
            region='us-east-2',
            secret_access_key='_222',
            security_group_id='sg-11111111',
            ssh_key_name='random_name',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='ec2-user',
            subnet_id='subnet_east_2',
            tests=['test_stuff', 'test_sev_snp'],
            log_callback=job.log_callback,
            prefix_name='mash',
            cpu_options={'AmdSevSnp': 'enabled'}
        )
        mock_call_2 = call(
            'ec2',
            access_key_id='222_',
            cleanup=True,
            description=None,
            distro='sles',
            image_id='ami-321',
            instance_type='m6a.large',
            timeout=600,
            log_level=10,
            region='us-east-2',
            secret_access_key='_222',
            security_group_id='sg-11111111',
            ssh_key_name='random_name',
            ssh_private_key_file='private_ssh_key.file',
            ssh_user='ec2-user',
            subnet_id='subnet_east_2',
            tests=['test_stuff'],
            log_callback=job.log_callback,
            prefix_name='mash',
            cpu_options={}
        )

        # assert mock_test_image.mock_calls == [mock_call_1, mock_call_2]
        assert mock_call_1 in mock_test_image.mock_calls
        assert mock_call_2 in mock_test_image.mock_calls

        mock_cleanup_image.assert_has_calls([
            call(
                '111_',
                '_111',
                ANY,
                ANY,
                image_id='ami-123'
            ),
            call(
                '222_',
                '_222',
                ANY,
                ANY,
                image_id='ami-321'
            )
        ])
        job._log_callback.warning.reset_mock()

        # Exception in test
        mock_test_image.side_effect = Exception('Tests broken!')
        job.log_callback.reset_mock()
        ec2_setup.reset_mock()
        job.run_job()
        job._log_callback.warning.assert_has_calls([
            call('Image tests failed in region: us-east-2.')
        ])
        assert 'Tests broken!' in job._log_callback.error.mock_calls[1][1][0]
        assert ec2_setup.clean_up.call_count == 1

        # NO TEST REGIONS
        mock_create_ssh_key_pair.reset_mock()
        job = EC2TestJob(self.job_config, self.config)
        job._log_callback = Mock()

        mock_create_ssh_key_pair.assert_called_once_with('private_ssh_key.file')

        job.test_regions = {}
        with pytest.raises(MashTestException) as exc:
            job.run_job()
        assert 'At least one partition is required' in str(exc)
        assert job._log_callback.error.called

    @patch('mash.services.test.ec2_job.create_ssh_key_pair')
    def test_ec2_skip_test(
        self,
        mock_create_ssh_key_pair
    ):
        job = EC2TestJob(self.job_config, self.config)
        job._log_callback = Mock()
        job.tests = []

        job.run_job()

        job._log_callback.info.assert_called_once_with(
            'Skipping test service, no tests provided.'
        )
