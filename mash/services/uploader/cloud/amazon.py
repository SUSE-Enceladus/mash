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
from tempfile import NamedTemporaryFile
from collections import namedtuple
from ec2utils.ec2uploadimg import EC2ImageUploader

# project
from mash.services.uploader.cloud.base import UploadBase
from mash.mash_exceptions import MashUploadException
from mash.utils.ec2 import get_client
from mash.utils.mash_utils import generate_name


class UploadAmazon(UploadBase):
    """
    Implements system image upload to Amazon

    Amazon specific custom arguments:

    For upload to Amazon the ec2uploadimg python interface
    is used. The custom parameters are passed in one by one
    to this application.

    .. code:: python

        custom_args={
            'ssh_key_pair_name': 'name_of_ssh_keypair_for_upload',
            'verbose': True|False,
            'launch_ami': 'name_of_helper_ami_to_run_for_upload',
            'use_grub2': True|False,
            'use_private_ip': True|False,
            'root_volume_size': 'size_of_attached_root_volume',
            'image_virt_type': 'virtualization_type',
            'launch_inst_type': 'helper_instance_type',
            'inst_user_name': 'user_name_for_ssh_access_to_helper_instance',
            'ssh_timeout': 'ssh_timeout_sec',
            'wait_count': 'number_of_wait_cycles',
            'vpc_subnet_id': 'vpc_subnet_id_for_helper_instance',
            'ssh_key_private_key_file': 'path_to_ssh_private_key_file',
            'security_group_ids': 'security_group_id_for_helper_instance',
            'sriov_type': 'SRIOV type',
            'access_key': 'helper_instance_access_key',
            'ena_support': True|False,
            'backing_store': 'backing_store_type',
            'secret_key': 'helper_instance_secret_access_key'
        }
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

        self.ec2_upload_parameters['access_key'] = \
            self.credentials['access_key_id']
        self.ec2_upload_parameters['secret_key'] = \
            self.credentials['secret_access_key']

        if self.custom_args:
            if 'region' in self.custom_args:
                self.region = self.custom_args['region']
                del self.custom_args['region']

            if 'account' in self.custom_args:
                del self.custom_args['account']

            self.ec2_upload_parameters.update(self.custom_args)

    def upload(self):
        try:
            ec2_client = get_client(
                'ec2', self.credentials['access_key_id'],
                self.credentials['secret_access_key'], self.region
            )

            # NOTE: Temporary ssh keys:
            # The temporary creation and registration of a ssh key pair
            # is considered a workaround implementation which should be better
            # covered by the EC2ImageUploader code. Due to a lack of
            # development resources in the ec2utils.ec2uploadimg project and
            # other peoples concerns for just using a generic mash ssh key
            # for the upload, the private _create_key_pair and _delete_key_pair
            # methods exists and could be hopefully replaced by a better
            # concept in the near future.
            ssh_key_pair = self._create_key_pair(ec2_client)

            self.ec2_upload_parameters['ssh_key_pair_name'] = \
                ssh_key_pair.name
            self.ec2_upload_parameters['ssh_key_private_key_file'] = \
                ssh_key_pair.private_key_file.name

            ec2_upload = EC2ImageUploader(
                **self.ec2_upload_parameters
            )

            ec2_upload.set_region(self.region)

            ami_id = ec2_upload.create_image(
                self.system_image_file
            )
            return ami_id, self.region
        except Exception as e:
            raise MashUploadException(
                'Upload to Amazon EC2 failed with: {0}'.format(e)
            )
        finally:
            self._delete_key_pair(
                ec2_client, ssh_key_pair
            )

    def _create_key_pair(self, ec2_client):
        ssh_key_pair_type = namedtuple(
            'ssh_key_pair_type', ['name', 'private_key_file']
        )
        private_key_file = NamedTemporaryFile()
        key_pair_name = 'mash-{0}'.format(generate_name())
        ssh_key = ec2_client.create_key_pair(KeyName=key_pair_name)
        with open(private_key_file.name, 'w') as private_key:
            private_key.write(ssh_key['KeyMaterial'])
        return ssh_key_pair_type(
            name=key_pair_name,
            private_key_file=private_key_file
        )

    def _delete_key_pair(self, ec2_client, ssh_key_pair):
        ec2_client.delete_key_pair(KeyName=ssh_key_pair.name)
        private_key_file = ssh_key_pair.private_key_file
        del private_key_file
