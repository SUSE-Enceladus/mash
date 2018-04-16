from pytest import raises
from unittest.mock import Mock, patch

from test.unit.test_helper import (
    patch_open, context_manager
)

from mash.services.uploader.cloud.amazon import UploadAmazon
from mash.mash_exceptions import MashUploadException


class TestUploadAmazon(object):
    def setup(self):
        self.credentials = Mock()
        self.credentials = {
            'access_key_id': 'access-key',
            'secret_access_key': 'secret-access-key'
        }
        custom_args = {
            'image_arch': 'x86_64',
            'launch_ami': 'ami-bc5b48d0',
            'sriov_type': 'simple',
            'ena_support': True,
            'region': 'us-east-1',
            'account': 'mash-account'
        }
        self.uploader = UploadAmazon(
            self.credentials, 'file', 'name', 'description', custom_args
        )

    @patch('mash.services.uploader.cloud.amazon.get_client')
    @patch('mash.services.uploader.cloud.amazon.generate_name')
    @patch('mash.services.uploader.cloud.amazon.NamedTemporaryFile')
    @patch('mash.services.uploader.cloud.amazon.EC2ImageUploader')
    @patch_open
    def test_upload(
        self, mock_open, mock_EC2ImageUploader, mock_NamedTemporaryFile,
        mock_generate_name, mock_get_client
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
        assert self.uploader.upload() == ('ami_id', 'us-east-1')
        mock_get_client.assert_called_once_with(
            'ec2', 'access-key', 'secret-access-key', 'us-east-1'
        )
        mock_EC2ImageUploader.assert_called_once_with(
            access_key='access-key',
            backing_store='ssd',
            bootkernel=None,
            ena_support=True,
            image_arch='x86_64',
            image_description='description',
            image_name='name',
            image_virt_type='hvm',
            inst_user_name='ec2-user',
            launch_ami='ami-bc5b48d0',
            launch_inst_type='t2.micro',
            root_volume_size=10,
            running_id=None,
            secret_key='secret-access-key',
            security_group_ids='',
            sriov_type='simple',
            ssh_key_pair_name='mash-xxxx',
            ssh_key_private_key_file='tmpfile',
            ssh_timeout=300,
            use_grub2=True,
            use_private_ip=False,
            verbose=True,
            vpc_subnet_id='',
            wait_count=3
        )
        open_context.file_mock.write.assert_called_once_with('pkey')
        ec2_client.create_key_pair.assert_called_once_with(KeyName='mash-xxxx')
        ec2_client.delete_key_pair.assert_called_once_with(KeyName='mash-xxxx')
        ec2_upload.set_region.assert_called_once_with('us-east-1')
        ec2_upload.create_image.assert_called_once_with('file')
        ec2_upload.create_image.side_effect = Exception
        with raises(MashUploadException):
            self.uploader.upload()
