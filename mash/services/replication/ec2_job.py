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

from collections import defaultdict

from mash.mash_exceptions import MashReplicationException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.ec2 import get_client


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

    def _run_job(self):
        """
        Replicate image to all target regions in each source region.
        """
        self.status = SUCCESS
        self.source_region_results = defaultdict(dict)

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
        time.sleep(600)

        for target_region, reg_info in self.source_region_results.items():
            credential = reg_info['account']
            self._wait_on_image(
                credential, reg_info['image_id'], target_region
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

    def _wait_on_image(self, credential, image_id, region):
        """
        Wait on image to finish replicating in the given region.
        """
        if image_id:
            client = get_client(
                'ec2', credential['access_key_id'],
                credential['secret_access_key'], region
            )

            try:
                waiter = client.get_waiter('image_available')
                waiter.wait(
                    ImageIds=[image_id],
                    Filters=[{'Name': 'state', 'Values': ['available']}],
                )
            except Exception as e:
                # Log all errors instead of exiting on first exception.
                self.send_log(
                    'There was an error replicating image to {0}. {1}'
                    .format(region, e),
                    False
                )
                self.status = FAILED

    def image_exists(self, client, cloud_image_name):
        """
        Determine if image exists given image name.
        """
        images = client.describe_images(Owners=['self'])['Images']
        for image in images:
            if cloud_image_name == image.get('Name'):
                return True
        return False
