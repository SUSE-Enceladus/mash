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

import time

from botocore.exceptions import ClientError
from collections import defaultdict

from mash.mash_exceptions import MashReplicationException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.ec2 import get_client, describe_images


class EC2ReplicationJob(MashJob):
    """
    Class for an EC2 replication job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.image_description = self.job_config['image_description']
            self.replication_source_regions = \
                self.job_config['replication_source_regions']
        except KeyError as error:
            raise MashReplicationException(
                'EC2 replication jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.source_region_results = defaultdict(dict)

    def run_job(self):
        """
        Replicate image to all target regions in each source region.
        """
        self.status = SUCCESS
        self.source_region_results = defaultdict(dict)

        # Get all account credentials in one request
        accounts = []
        for source_region, reg_info in self.replication_source_regions.items():
            accounts.append(reg_info['account'])

        self.request_credentials(accounts)

        for source_region, reg_info in self.replication_source_regions.items():
            credential = self.credentials[reg_info['account']]

            self.send_log(
                'Replicating source region: {0} to the following regions: {1}.'
                .format(
                    source_region, ', '.join(reg_info['target_regions'])
                )
            )

            for target_region in reg_info['target_regions']:
                if source_region != target_region:
                    # Replicate image to all target regions
                    # for each source region
                    self.source_region_results[target_region]['image_id'] = \
                        self._replicate_to_region(
                            credential, self.source_regions[source_region],
                            source_region, target_region
                        )  # noqa: E123 Suppress erroneous flake8 warning.

                    # Save account along with results to prevent searching dict
                    # twice to find associated credentials on each waiter.
                    self.source_region_results[target_region]['account'] = \
                        credential

        # Wait for images to replicate, this will take time.
        time.sleep(300)

        for target_region, reg_info in self.source_region_results.items():
            credential = reg_info['account']

            if reg_info['image_id']:
                try:
                    self._wait_on_image(
                        credential['access_key_id'],
                        credential['secret_access_key'],
                        reg_info['image_id'],
                        target_region
                    )
                except Exception as error:
                    self.status = FAILED
                    self.send_log(
                        'Replication to {0} region failed: {1}'.format(
                            target_region,
                            error
                        )
                    )

    def _replicate_to_region(
        self, credential, image_id, source_region, target_region
    ):
        """
        Replicate image to the target region from the source region.
        """
        client = get_client(
            'ec2', credential['access_key_id'],
            credential['secret_access_key'], target_region
        )

        try:
            exists = self.image_exists(client, self.cloud_image_name)
            if not exists:
                new_image = client.copy_image(
                    Description=self.image_description,
                    Name=self.cloud_image_name,
                    SourceImageId=image_id,
                    SourceRegion=source_region,
                )
            else:
                new_image = {'ImageId': None}
        except Exception as e:
            raise MashReplicationException(
                'There was an error replicating image to {0}. {1}'
                .format(
                    target_region, e
                )
            )

        return new_image['ImageId']

    @staticmethod
    def _wait_on_image(access_key_id, secret_access_key, image_id, region):
        """
        Wait on image to finish replicating in the given region.
        """
        while True:
            client = get_client(
                'ec2',
                access_key_id,
                secret_access_key,
                region
            )

            try:
                images = describe_images(client, [image_id])
                state = images[0]['State']
            except (IndexError, KeyError, ClientError):
                raise MashReplicationException(
                    'The image with ID: {0} was not found.'.format(
                        image_id
                    )
                )

            if state == 'available':
                break
            elif state == 'failed':
                raise MashReplicationException(
                    'The image with ID: {0} reached a failed state.'.format(
                        image_id
                    )
                )
            elif state == 'pending':
                time.sleep(60)

    @staticmethod
    def image_exists(client, cloud_image_name):
        """
        Determine if image exists given image name.
        """
        images = describe_images(client)
        for image in images:
            if cloud_image_name == image.get('Name'):
                return True
        return False
