# Copyright (c) 2022 SUSE LLC.  All rights reserved.
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

import re

from ec2imgutils.ec2publishimg import EC2PublishImage

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS
from mash.utils.ec2 import get_client, start_mp_change_set
from mash.utils.mash_utils import format_string_with_date


class EC2MPPublishJob(MashJob):
    """
    Class for an EC2 marketplace publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.publish_regions = self.job_config['publish_regions']
            self.entity_id = self.job_config['entity_id']
            self.version_title = self.job_config['version_title']
            self.access_role_arn = self.job_config['access_role_arn']
            self.release_notes = self.job_config['release_notes']
            self.os_name = self.job_config['os_name']
            self.os_version = self.job_config['os_version']
            self.usage_instructions = self.job_config['usage_instructions']
            self.upgrade_instructions = self.job_config['upgrade_instructions']
            self.recommended_instance_type = \
                self.job_config['recommended_instance_type']
        except KeyError as error:
            raise MashPublishException(
                'EC2 MP publish Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.ssh_user = self.job_config.get('ssh_user', 'ec2-user')
        self.allow_copy = self.job_config.get('allow_copy', 'none')
        self.share_with = self.job_config.get('share_with', 'none')

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        # Get all account credentials in one request
        self.request_credentials(list(self.publish_regions.keys()), cloud='ec2')
        self.cloud_image_name = self.status_msg['cloud_image_name']

        timestamp = re.findall(r'\d{8}', self.cloud_image_name)[0]
        self.version_title = format_string_with_date(
            self.version_title,
            timestamp=timestamp
        )

        for account, region in self.publish_regions.items():
            creds = self.credentials[account]
            ami_id = self.status_msg['source_regions'][region]

            self.share_image(
                region,
                creds['access_key_id'],
                creds['secret_access_key']
            )

            client = get_client(
                'marketplace-catalog',
                creds['access_key_id'],
                creds['secret_access_key'],
                region
            )

            response = start_mp_change_set(
                client,
                self.entity_id,
                self.version_title,
                ami_id,
                self.access_role_arn,
                self.release_notes,
                self.os_name,
                self.os_version,
                self.usage_instructions,
                self.upgrade_instructions,
                self.recommended_instance_type,
                self.ssh_user
            )
            self.status_msg['change_set_id'] = response.get('ChangeSetId')
            self.log_callback.info(
                'Marketplace change set submitted. Change set id: '
                '{change_set}'.format(
                    change_set=self.status_msg['change_set_id']
                )
            )

    def share_image(self, region, access_key_id, secret_access_key):
        publish = EC2PublishImage(
            access_key=access_key_id,
            allow_copy=self.allow_copy,
            image_name=self.cloud_image_name,
            secret_key=secret_access_key,
            visibility=self.share_with,
            log_callback=self.log_callback
        )

        publish.set_region(region)
        try:
            publish.publish_images()
        except Exception as error:
            raise MashPublishException(
                'An error publishing image {0} in {1}. {2}'.format(
                    self.cloud_image_name, region, error
                )
            )
