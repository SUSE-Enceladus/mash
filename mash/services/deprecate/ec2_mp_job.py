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

from aws_mp_utils.changeset import start_mp_change_set
from aws_mp_utils.image import (
    create_restrict_version_change_doc,
    get_image_delivery_option_id,
)

from mash.mash_exceptions import MashDeprecateException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS
from mash.utils.ec2 import (
    get_session,
    get_image
)


class EC2MPDeprecateJob(MashJob):
    """
    Class for EC2 Marketplace restriction.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.deprecate_regions = self.job_config['deprecate_regions']
        except KeyError as error:
            raise MashDeprecateException(
                'EC2 deprecate Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.old_cloud_image_name = self.job_config.get(
            'old_cloud_image_name'
        )

        if self.job_config.get('entity_id'):
            self.entity_ids = [
                {
                    'entity_id': self.job_config['entity_id'],
                    'catalog': 'AWSMarketplace'
                }
            ]
        elif self.job_config.get('entity_ids'):
            self.entity_ids = self.job_config['entity_ids']
        else:
            raise MashDeprecateException(
                'EC2 MP publish Jobs require either an entity_id '
                'key or entity_ids key in the job doc.'
            )

    def run_job(self):
        """
        Restrict the image in each source region.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecate for the job.
            return

        # Get all account credentials in one request
        self.request_credentials(list(self.deprecate_regions.keys()), cloud='ec2')

        for account, region in self.deprecate_regions.items():
            credential = self.credentials[account]

            session = get_session(
                credential['access_key_id'],
                credential['secret_access_key'],
                region
            )
            mp_client = session.client('marketplace-catalog')
            old_image = get_image(
                session.client('ec2'),
                self.old_cloud_image_name
            )

            for entity in self.entity_ids:
                entity_id = entity['entity_id']
                delivery_option_id = get_image_delivery_option_id(
                    mp_client,
                    entity_id,
                    old_image['ImageId']
                )
                restrict_version_doc = create_restrict_version_change_doc(
                    entity_id=entity_id,
                    delivery_option_id=delivery_option_id
                )

                response = start_mp_change_set(
                    mp_client,
                    change_set=[
                        self.status_msg['add_version_docs'][entity_id],
                        restrict_version_doc
                    ],
                    catalog=entity['catalog']
                )

                change_set_id = response.get('ChangeSetId')
                self.status_msg['change_set_ids'][entity_id] = change_set_id
                self.log_callback.info(
                    'Marketplace change set submitted. Change set id: '
                    '{change_set}'.format(
                        change_set=change_set_id
                    )
                )

            self.status_msg.pop('add_version_docs')
