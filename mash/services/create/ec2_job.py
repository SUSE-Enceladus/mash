# Copyright (c) 2023 SUSE LLC.  All rights reserved.
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

from ec2imgutils.ec2uploadimg import EC2ImageUploader

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.ec2 import (
    get_client,
    cleanup_ec2_image,
    image_exists,
    cleanup_all_ec2_images
)
from mash.utils.mash_utils import (
    format_string_with_date,
    timestamp_from_epoch
)
from mash.services.status_levels import SUCCESS, FAILED


class EC2CreateJob(MashJob):
    """
    Implements VM image upload/create to Amazon.

    Amazon specific custom arguments:

    For upload to Amazon the ec2uploadimg python interface
    is used. The image is written directly to an EBS snapshot
    using the EBS direct APIs, no helper instance is needed.
    With the root swap method the image is written the same way
    and a donor instance, which is never accessed, provides the
    meta data of the new image.
    The custom parameters are passed in one by one to this
    application.
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
        self.use_build_time = self.job_config.get('use_build_time')
        self.force_replace_image = self.job_config.get('force_replace_image')
        self.tpm_support = self.job_config.get('tpm_support')
        self.launch_inst_type = self.job_config.get('launch_inst_type')
        self.boot_firmware = self.job_config.get(
            'boot_firmware',
            ['uefi-preferred']
        )
        self.imds_version = self.job_config.get('imds_version', '')
        self.root_volume_size = self.job_config.get('root_volume_size', 10)
        self.upload_wait_count = self.job_config.get('upload_wait_count', 3)
        self.image_tags = self.job_config.get('image_tags')
        self.upload_options = {
            option: self.job_config[option]
            for option in (
                'upload_workers', 'upload_retries', 'upload_timeout'
            )
            if self.job_config.get(option)
        }

        # EC2 images only support one firmware
        self.boot_firmware = self.boot_firmware[0]

        if self.boot_firmware == 'bios':
            # Translate to EC2 lingo
            self.boot_firmware = 'legacy-bios'

        if self.arch == 'aarch64':
            self.arch = 'arm64'

    def run_job(self):
        self.status = SUCCESS
        self.status_msg['source_regions'] = {}
        self.log_callback.info('Creating image.')

        timestamp = None
        build_time = self.status_msg.get('build_time', 'unknown')

        if self.use_build_time and (build_time != 'unknown'):
            timestamp = timestamp_from_epoch(build_time)
        elif self.use_build_time and (build_time == 'unknown'):
            raise MashUploadException(
                'use_build_time set for job but build time is unknown.'
            )

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name,
            timestamp=timestamp
        )
        self.status_msg['cloud_image_name'] = self.cloud_image_name

        self.ec2_upload_parameters = {
            'image_name': self.cloud_image_name,
            'image_description': self.cloud_image_description,
            'image_arch': self.arch,
            'root_volume_size': self.root_volume_size,
            'wait_count': self.upload_wait_count,
            'sriov_type': 'simple',
            'access_key': None,
            'ena_support': True,
            'backing_store': 'gp3',
            'secret_key': None,
            'billing_codes': None,
            'log_callback': self.log_callback,
            'boot_mode': self.boot_firmware,
            'image_tags': self.image_tags
        }
        self.ec2_upload_parameters.update(self.upload_options)

        if self.tpm_support:
            self.ec2_upload_parameters['tpm_support'] = self.tpm_support

        if self.imds_version:
            self.ec2_upload_parameters['imds_support'] = self.imds_version

        # Get all account credentials in one request
        accounts = []
        for region, info in self.target_regions.items():
            accounts.append(info['account'])

        self.request_credentials(accounts)

        for region, info in self.target_regions.items():
            self.status_msg['source_regions'][region] = None
            account = info['account']
            credentials = self.credentials[account]

            use_root_swap = info.get('use_root_swap', False)

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

                exists = image_exists(ec2_client, self.cloud_image_name)
                if exists and not self.force_replace_image:
                    raise MashUploadException(
                        '{image_name} already exists. '
                        'Use force_replace_image to '
                        'replace the existing image.'.format(
                            image_name=self.cloud_image_name
                        )
                    )
                elif exists and self.force_replace_image:
                    cleanup_all_ec2_images(
                        credentials['access_key_id'],
                        credentials['secret_access_key'],
                        self.log_callback,
                        info['regions'],
                        self.cloud_image_name
                    )

                upload_parameters = dict(self.ec2_upload_parameters)
                if use_root_swap:
                    # The donor instance provides the meta data of the
                    # image. It is launched in the subnet if one is set,
                    # otherwise in the default VPC of the region.
                    upload_parameters['launch_ami'] = info.get('helper_image')
                    upload_parameters['launch_inst_type'] = \
                        self.launch_inst_type or 't3.micro'
                    upload_parameters['vpc_subnet_id'] = \
                        info.get('subnet') or ''

                ec2_upload = EC2ImageUploader(**upload_parameters)

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
                break  # No need to continue if one account fails

        if self.status != SUCCESS:
            for region, info in self.target_regions.items():
                credentials = self.credentials[info['account']]

                if self.status_msg['source_regions'].get(region):
                    # Only cleanup regions that passed

                    try:
                        cleanup_ec2_image(
                            credentials['access_key_id'],
                            credentials['secret_access_key'],
                            self.log_callback,
                            region,
                            image_id=self.status_msg['source_regions'][region]
                        )
                    except Exception as error:
                        self.log_callback.warning(
                            'Failed to cleanup image: {0} in region {1}.'
                            ' {2}'.format(
                                self.status_msg['source_regions'][region],
                                region,
                                error
                            )
                        )
