# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#
from ec2utils.ec2uploadimg import EC2ImageUploader

# project
from mash.services.uploader.cloud.base import UploadBase
from mash.mash_exceptions import MashUploadException


class UploadAmazon(UploadBase):
    """
    Implements system image upload to Amazon
    """
    def post_init(self):
        self.region = 'eu-central-1'
        self.ec2_upload_parameters = {
            'image_name': self.cloud_image_name,
            'image_description': self.cloud_image_description,
            'ssh_key_pair_name': None,
            'verbose': True,
            'image_arch': 'x86_64',
            'launch_ami': None,
            'use_grub2': True,
            'use_private_ip': False,
            'root_volume_size': 10,
            'image_virt_type': 'hvm',
            'launch_inst_type': 't2.micro',
            'bootkernel': None,
            'inst_user_name': 'ec2-user',
            'ssh_timeout': 300,
            'wait_count': 3,
            'vpc_subnet_id': '',
            'ssh_key_private_key_file': None,
            'security_group_ids': '',
            'sriov_type': 'simple',
            'access_key': None,
            'ena_support': True,
            'backing_store': 'ssd',
            'running_id': None,
            'secret_key': None
        }
        self.ec2_upload_parameters.update(
            self.credentials.get_credentials()
        )
        if self.custom_args:
            if 'region' in self.custom_args:
                self.region = self.custom_args['region']
                del self.custom_args['region']

            self.ec2_upload_parameters.update(self.custom_args)

        self.ec2 = EC2ImageUploader(
            **self.ec2_upload_parameters
        )

    def upload(self):
        try:
            self.ec2.set_region(self.region)
            return self.ec2.create_image(
                self.system_image_file
            )
        except Exception as e:
            raise MashUploadException(
                'Upload to Amazon EC2 failed with: {0}'.format(e)
            )
