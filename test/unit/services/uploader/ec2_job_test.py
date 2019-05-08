from pytest import raises
from unittest.mock import Mock, patch

from test.unit.test_helper import (
    patch_open, context_manager
)

from mash.services.uploader.ec2_job import EC2UploaderJob
from mash.mash_exceptions import MashUploadException
from mash.services.uploader.config import UploaderConfig


class TestAmazonUploaderJob(object):
    def setup(self):
        self.config = UploaderConfig(
            config_file='../data/mash_config.yaml'
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
            'last_service': 'uploader',
            'cloud': 'ec2',
            'utctime': 'now',
            'target_regions': {
                'us-east-1': {
                    'account': 'test',
                    'helper_image': 'ami-bc5b48d0',
                    'billing_codes': None
                }
            },
            'cloud_image_name': 'name',
            'image_description': 'description'
        }
        self.job = EC2UploaderJob(job_doc, self.config)
        self.job.image_file = ['file']
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            EC2UploaderJob(job_doc, self.config)

        job_doc['target_regions'] = {'name': {'account': 'info'}}
        with raises(MashUploadException):
            EC2UploaderJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'name'
        with raises(MashUploadException):
            EC2UploaderJob(job_doc, self.config)

    @patch('mash.services.uploader.ec2_job.EC2Setup')
    @patch('mash.services.uploader.ec2_job.get_client')
    @patch('mash.services.uploader.ec2_job.generate_name')
    @patch('mash.services.uploader.ec2_job.NamedTemporaryFile')
    @patch('mash.services.uploader.ec2_job.EC2ImageUploader')
    @patch_open
    def test_upload(
        self, mock_open, mock_EC2ImageUploader, mock_NamedTemporaryFile,
        mock_generate_name, mock_get_client, mock_ec2_setup
    ):
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

        self.job._run_job()
        mock_get_client.assert_called_once_with(
            'ec2', 'access-key', 'secret-access-key', 'us-east-1'
        )
        mock_EC2ImageUploader.assert_called_once_with(
            access_key='access-key',
            backing_store='ssd',
            billing_codes=None,
            bootkernel=None,
            ena_support=True,
            image_arch='arm64',
            image_description='description',
            image_name='name',
            image_virt_type='hvm',
            inst_user_name='ec2-user',
            launch_ami='ami-bc5b48d0',
            launch_inst_type='t2.micro',
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
            verbose=True,
            vpc_subnet_id='subnet-123456789',
            wait_count=3
        )
        open_context.file_mock.write.assert_called_once_with('pkey')

        ec2_client.create_key_pair.assert_called_once_with(KeyName='mash-xxxx')
        ec2_client.delete_key_pair.assert_called_once_with(KeyName='mash-xxxx')

        ec2_upload.set_region.assert_called_once_with('us-east-1')
        ec2_upload.create_image.assert_called_once_with('file')

        ec2_setup.clean_up.assert_called_once_with()
        ec2_upload.create_image.side_effect = Exception

        with raises(MashUploadException):
            self.job._run_job()
