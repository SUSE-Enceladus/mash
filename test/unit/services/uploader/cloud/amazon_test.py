from pytest import raises
from unittest.mock import Mock

from mash.services.uploader.cloud.amazon import UploadAmazon
from mash.mash_exceptions import MashUploadException

import mash


class TestUploadAmazon(object):
    def setup(self):
        self.ec2 = Mock()
        mash.services.uploader.cloud.amazon.EC2ImageUploader = self.ec2
        self.credentials = Mock()
        self.credentials.get_credentials.return_value = {
            'ssh_key_pair_name': 'name',
            'ssh_key_private_key_file': '/some/path/to/private/key',
            'access_key': 'access-key',
            'secret_key': 'secret-access-key'
        }
        custom_args = {
            'image_arch': 'x86_64',
            'launch_ami': 'ami-bc5b48d0',
            'sriov_type': 'simple',
            'ena_support': True,
            'region': 'us-east-1'
        }
        self.uploader = UploadAmazon(
            self.credentials, 'file', 'name', 'description', custom_args
        )
        self.ec2.assert_called_once_with(
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
            ssh_key_pair_name='name',
            ssh_key_private_key_file='/some/path/to/private/key',
            ssh_timeout=300,
            use_grub2=True,
            use_private_ip=False,
            verbose=True,
            vpc_subnet_id='',
            wait_count=3
        )

    def test_upload(self):
        self.uploader.ec2.create_image.return_value = 'ami_id'
        assert self.uploader.upload() == ['ami_id', 'us-east-1']
        self.uploader.ec2.set_region.assert_called_once_with('us-east-1')
        self.uploader.ec2.create_image.assert_called_once_with('file')
        self.uploader.ec2.create_image.side_effect = Exception
        with raises(MashUploadException):
            self.uploader.upload()
