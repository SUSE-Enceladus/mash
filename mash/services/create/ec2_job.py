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
from mash.utils.ec2 import (
    get_client,
    get_vpc_id_from_subnet,
    cleanup_ec2_image
)
from mash.utils.mash_utils import format_string_with_date, generate_name
from mash.services.status_levels import SUCCESS, FAILED


class EC2CreateJob(MashJob):
    """
    Implements VM image upload/create to Amazon.

    Amazon specific custom arguments:

    For upload to Amazon the ec2uploadimg python interface
    is used. The custom parameters are passed in one by one
    to this application.
    """

    def post_init(self):
        try:
            self.target_regions = self.job_config['target_regions']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
            self.cloud_image_description = \
                self.job_config['image_description']
        except KeyError as error:
            raise MashUploadException(
                'EC2 create jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.arch = self.job_config.get('cloud_architecture', 'x86_64')

        if self.arch == 'aarch64':
            self.arch = 'arm64'

    def run_job(self):
        self.status = SUCCESS
        self.status_msg['source_regions'] = {}
        self.log_callback.info('Creating image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )
        self.status_msg['cloud_image_name'] = self.cloud_image_name

        self.ec2_upload_parameters = {
            'image_name': self.cloud_image_name,
            'image_description': self.cloud_image_description,
            'ssh_key_pair_name': None,
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
            'billing_codes': None,
            'log_callback': self.log_callback
        }

        # Get all account credentials in one request
        accounts = []
        for region, info in self.target_regions.items():
            accounts.append(info['account'])

        self.request_credentials(accounts)

        for region, info in self.target_regions.items():
            self.status_msg['source_regions'][region] = None
            account = info['account']
            credentials = self.credentials[account]

            use_root_swap = info['use_root_swap']
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
                # helper image, unless a subnet was specified.
                # This provides a security group with an open ssh port.
                ec2_setup = EC2Setup(
                    credentials['access_key_id'],
                    region,
                    credentials['secret_access_key'],
                    None,
                    log_callback=self.log_callback
                )

                subnet_id = info.get('subnet')
                if subnet_id:
                    vpc_id = get_vpc_id_from_subnet(ec2_client, subnet_id)
                    security_group_id = ec2_setup.create_security_group(vpc_id=vpc_id)
                else:
                    subnet_id = ec2_setup.create_vpc_subnet()
                    security_group_id = ec2_setup.create_security_group()

                self.ec2_upload_parameters['vpc_subnet_id'] = subnet_id
                self.ec2_upload_parameters['security_group_ids'] = \
                    security_group_id

                ec2_upload = EC2ImageUploader(
                    **self.ec2_upload_parameters
                )

                ec2_upload.set_region(region)

                if use_root_swap:
                    ami_id = ec2_upload.create_image_use_root_swap(
                        self.status_msg['image_file']
                    )
                else:
                    ami_id = ec2_upload.create_image(
                        self.status_msg['image_file']
                    )

                self.status_msg['source_regions'][region] = ami_id
                self.log_callback.info(
                    'Created image has ID: {0} in region {1}'.format(
                        ami_id, region
                    )
                )
            except Exception as error:
                self.status = FAILED
                msg = 'Image creation in account {0} failed with: {1}'.format(
                    account,
                    error
                )
                self.add_error_msg(msg)
                self.log_callback.error(msg)
            finally:
                self._delete_key_pair(
                    ec2_client, ssh_key_pair
                )
                ec2_setup.clean_up()

        if self.status != SUCCESS:
            for region, info in self.target_regions.items():
                credentials = self.credentials[info['account']]

                if self.status_msg['source_regions'].get(region):
                    # Only cleanup regions that passed
                    cleanup_ec2_image(
                        credentials['access_key_id'],
                        credentials['secret_access_key'],
                        self.log_callback,
                        region,
                        self.status_msg['source_regions'][region]
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
