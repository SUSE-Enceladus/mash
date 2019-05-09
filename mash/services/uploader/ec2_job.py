# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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
from ec2imgutils.ec2uploadimg import EC2ImageUploader
from ec2imgutils.ec2setup import EC2Setup

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.ec2 import get_client
from mash.utils.mash_utils import format_string_with_date, generate_name
from mash.services.status_levels import SUCCESS


class EC2UploaderJob(MashJob):
    """
    Implements system image upload to Amazon

    Amazon specific custom arguments:

    For upload to Amazon the ec2uploadimg python interface
    is used. The custom parameters are passed in one by one
    to this application.
    """

    def post_init(self):
        self._image_file = None
        self.source_regions = {}

        try:
            self.target_regions = self.job_config['target_regions']
            self.cloud_image_name = self.job_config['cloud_image_name']
            self.cloud_image_description = \
                self.job_config['image_description']
        except KeyError as error:
            raise MashUploadException(
                'EC2 uploader jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.arch = self.job_config.get('cloud_architecture', 'x86_64')

        if self.arch == 'aarch64':
            self.arch = 'arm64'

    def run_job(self):
        self.status = SUCCESS
        self.send_log('Uploading image.')

        cloud_image_name = format_string_with_date(
            self.cloud_image_name
        )

        self.ec2_upload_parameters = {
            'image_name': cloud_image_name,
            'image_description': self.cloud_image_description,
            'ssh_key_pair_name': None,
            'verbose': True,
            'image_arch': self.arch,
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
            'secret_key': None,
            'billing_codes': None
        }

        for region, info in self.target_regions.items():
            account = info['account']
            credentials = self.credentials[account]

            self.ec2_upload_parameters['launch_ami'] = info['helper_image']
            self.ec2_upload_parameters['billing_codes'] = \
                info['billing_codes']

            self.ec2_upload_parameters['access_key'] = \
                credentials['access_key_id']
            self.ec2_upload_parameters['secret_key'] = \
                credentials['secret_access_key']

            try:
                ec2_client = get_client(
                    'ec2', credentials['access_key_id'],
                    credentials['secret_access_key'], region
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

                # Create a temporary vpc, subnet and security group for the
                # helper image. This provides a security group with an open
                # ssh port.
                ec2_setup = EC2Setup(
                    credentials['access_key_id'],
                    region,
                    credentials['secret_access_key'],
                    None,
                    False
                )
                vpc_subnet_id = ec2_setup.create_vpc_subnet()
                security_group_id = ec2_setup.create_security_group()

                self.ec2_upload_parameters['vpc_subnet_id'] = vpc_subnet_id
                self.ec2_upload_parameters['security_group_ids'] = \
                    security_group_id

                ec2_upload = EC2ImageUploader(
                    **self.ec2_upload_parameters
                )

                ec2_upload.set_region(region)

                ami_id = ec2_upload.create_image(
                    self.image_file[0]
                )
                self.source_regions[region] = ami_id
                self.send_log(
                    'Uploaded image has ID: {0} in region {1}'.format(
                        ami_id, region
                    )
                )
            except Exception as e:
                raise MashUploadException(
                    'Upload to Amazon EC2 failed with: {0}'.format(e)
                )
            finally:
                self._delete_key_pair(
                    ec2_client, ssh_key_pair
                )
                ec2_setup.clean_up()

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

    @property
    def image_file(self):
        """System image file property."""
        return self._image_file

    @image_file.setter
    def image_file(self, system_image_file):
        """
        Setter for image_file list.
        """
        self._image_file = system_image_file
