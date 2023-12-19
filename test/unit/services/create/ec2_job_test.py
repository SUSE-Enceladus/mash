from pytest import raises
from unittest.mock import Mock, patch

from test.unit.test_helper import (
    patch_open, context_manager
)

from mash.services.create.ec2_job import EC2CreateJob
from mash.mash_exceptions import MashUploadException
from mash.services.base_config import BaseConfig


class TestAmazonCreateJob(object):
    def setup(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'access_key_id': 'access-key',
                'secret_access_key': 'secret-access-key'
            }
        }
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'create',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'utctime': 'now',
            'target_regions': {
                'us-east-1': {
                    'account': 'test',
                    'helper_image': 'ami-bc5b48d0',
                    'billing_codes': None,
                    'use_root_swap': False,
                    'subnet': 'subnet-123456789',
                    'regions': ['us-east-1', 'us-east-2']
                }
            },
            'cloud_image_name': 'name v{date}',
            'image_description': 'description',
            'use_build_time': True,
            'tpm_support': 'v2.0',
            'launch_inst_type': 'm1.large'
        }
        self.job = EC2CreateJob(job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.status_msg['image_file'] = 'file'
        self.job.status_msg['build_time'] = '1601061355'
        self.job.status_msg['source_regions'] = {'us-east-1': 'ami_id'}
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'create',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

        job_doc['target_regions'] = {'name': {'account': 'info'}}
        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'name'
        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    @patch('mash.services.create.ec2_job.cleanup_all_ec2_images')
    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.cleanup_ec2_image')
    @patch('mash.services.create.ec2_job.get_vpc_id_from_subnet')
    @patch('mash.services.create.ec2_job.EC2Setup')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.generate_name')
    @patch('mash.services.create.ec2_job.NamedTemporaryFile')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    @patch_open
    def test_create(
        self, mock_open, mock_EC2ImageUploader, mock_NamedTemporaryFile,
        mock_generate_name, mock_get_client, mock_ec2_setup,
        mock_get_vpc_id_from_subnet, mock_cleanup_image,
        mock_image_exists, mock_cleanup_all_images
    ):
        mock_image_exists.return_value = False

        open_context = context_manager()
        mock_open.return_value = open_context.context_manager_mock

        ec2_upload = Mock()
        ec2_upload.create_image.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        tempfile = Mock()
        tempfile.name = 'tmpfile'
        mock_NamedTemporaryFile.return_value = tempfile

        ec2_client = Mock()
        # https://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.create_key_pair
        ec2_client.create_key_pair.return_value = {
            'KeyFingerprint': 'fingerprint',
            'KeyMaterial': 'pkey',
            'KeyName': 'name'
        }
        mock_get_client.return_value = ec2_client

        mock_generate_name.return_value = 'xxxx'

        ec2_setup = Mock()
        ec2_setup.create_vpc_subnet.return_value = 'subnet-123456789'
        ec2_setup.create_security_group.return_value = 'sg-123456789'
        mock_ec2_setup.return_value = ec2_setup

        mock_get_vpc_id_from_subnet.return_value = 'vpc-123456789'

        self.job.run_job()
        mock_get_client.assert_called_once_with(
            'ec2', 'access-key', 'secret-access-key', 'us-east-1'
        )
        mock_EC2ImageUploader.assert_called_once_with(
            access_key='access-key',
            backing_store='gp3',
            billing_codes=None,
            bootkernel=None,
            ena_support=True,
            image_arch='arm64',
            image_description='description',
            image_name='name v20200925',
            image_virt_type='hvm',
            inst_user_name='ec2-user',
            launch_ami='ami-bc5b48d0',
            launch_inst_type='m1.large',
            root_volume_size=10,
            running_id=None,
            secret_key='secret-access-key',
            security_group_ids='sg-123456789',
            sriov_type='simple',
            ssh_key_pair_name='mash-xxxx',
            ssh_key_private_key_file='tmpfile',
            ssh_timeout=300,
            use_grub2=True,
            use_private_ip=False,
            vpc_subnet_id='subnet-123456789',
            wait_count=3,
            log_callback=self.job._log_callback,
            tpm_support='v2.0',
            boot_mode='uefi-preferred'
        )
        open_context.file_mock.write.assert_called_once_with('pkey')
        ec2_client.create_key_pair.assert_called_once_with(KeyName='mash-xxxx')
        ec2_client.delete_key_pair.assert_called_once_with(KeyName='mash-xxxx')
        ec2_upload.set_region.assert_called_once_with('us-east-1')
        ec2_upload.create_image.assert_called_once_with('file')
        ec2_setup.clean_up.assert_called_once_with()

        # Image create error
        ec2_upload.create_image.side_effect = ['ami_id', Exception('Failed!')]
        mock_cleanup_image.side_effect = Exception
        self.job.target_regions['us-east-2'] = {
            'account': 'test',
            'helper_image': 'ami-bc5b48d0',
            'billing_codes': None,
            'use_root_swap': False,
            'subnet': 'subnet-123456789'
        }

        self.job.run_job()

        self.job._log_callback.error.assert_called_once_with(
            'Image creation in account test failed with: Failed!'
        )
        mock_cleanup_image.assert_called_once_with(
            'access-key',
            'secret-access-key',
            self.job._log_callback,
            'us-east-1',
            image_id='ami_id'
        )

        # Image exists and not force replace image
        mock_image_exists.return_value = True
        self.job.run_job()

        msg = 'Image creation in account test failed with: name' \
              ' v20200925 already exists. Use force_replace_image ' \
              'to replace the existing image.'
        assert msg in self.job.status_msg['errors']

        # Image exists and force replace image
        self.job.force_replace_image = True
        self.job.run_job()
        assert mock_cleanup_all_images.call_count == 1

    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.EC2Setup')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.generate_name')
    @patch('mash.services.create.ec2_job.NamedTemporaryFile')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    @patch_open
    def test_create_root_swap(
        self, mock_open, mock_EC2ImageUploader, mock_NamedTemporaryFile,
        mock_generate_name, mock_get_client, mock_ec2_setup,
        mock_image_exists
    ):
        mock_image_exists.return_value = False

        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'upload',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'utctime': 'now',
            'target_regions': {
                'us-east-1': {
                    'account': 'test',
                    'helper_image': 'ami-bc5b48d0',
                    'billing_codes': None,
                    'use_root_swap': True
                }
            },
            'cloud_image_name': 'name',
            'image_description': 'description'
        }
        self.job = EC2CreateJob(job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.status_msg['image_file'] = 'file'
        self.job.status_msg['source_regions'] = {'us-east-1': 'ami_id'}
        self.job.credentials = self.credentials

        open_context = context_manager()
        mock_open.return_value = open_context.context_manager_mock

        ec2_upload = Mock()
        ec2_upload.create_image.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        tempfile = Mock()
        tempfile.name = 'tmpfile'
        mock_NamedTemporaryFile.return_value = tempfile

        ec2_client = Mock()
        # https://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.create_key_pair
        ec2_client.create_key_pair.return_value = {
            'KeyFingerprint': 'fingerprint',
            'KeyMaterial': 'pkey',
            'KeyName': 'name'
        }
        mock_get_client.return_value = ec2_client

        mock_generate_name.return_value = 'xxxx'

        ec2_setup = Mock()
        ec2_setup.create_vpc_subnet.return_value = 'subnet-123456789'
        ec2_setup.create_security_group.return_value = 'sg-123456789'
        mock_ec2_setup.return_value = ec2_setup

        self.job.run_job()

        ec2_upload.create_image_use_root_swap.assert_called_once_with('file')
