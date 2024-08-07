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

from mash.mash_exceptions import MashTestPreparationException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.ec2 import get_client, describe_images


class EC2TestPreparationJob(MashJob):
    """
    Class for an EC2 test preparation job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.test_preparation_regions = \
                self.job_config['test_preparation_regions']
        except KeyError as error:
            raise MashTestPreparationException(
                'EC2 test preparation jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.test_region_results = defaultdict(dict)

    def run_job(self):
        """
        Replicate image to all target regions in each source region.
        """
        self.status = SUCCESS
        self.status_msg['test_regions'] = {}
        self.test_preparation_region_results = defaultdict(dict)
        self.cloud_image_name = self.status_msg['cloud_image_name']

        # Get all account credentials in one request
        accounts = []
        for source_region, reg_info in self.test_preparation_regions.items():
            accounts.append(reg_info['account'])

        self.request_credentials(accounts)

        for source_region, reg_info in self.test_preparation_regions.items():
            # Replicate image to all test regions
            # for each source region
            credential = self.credentials[reg_info['account']]

            self.log_callback.info(
                'Replicating source region: {0} to the following regions: {1}.'
                .format(
                    source_region, ', '.join(reg_info['test_regions'])
                )
            )

            for test_region in reg_info['test_regions']:
                image_id = self._replicate_to_region(
                    credential,
                    self.status_msg['source_regions'][source_region],
                    source_region,
                    test_region
                )

                self.log_callback.info(
                    'Image  was replicated as {0} in {1} region.'
                    'Image is not ready yet.'
                    .format(image_id, test_region)
                )

                self.status_msg['test_regions'][test_region] = image_id
                self.test_region_results[test_region]['image_id'] = \
                    image_id

                # Save account along with results to prevent searching dict
                # twice to find associated credentials on each waiter.
                self.test_region_results[test_region]['credential'] = \
                    credential

        if self.test_region_results:
            self.log_callback.info('Waiting for images to replicate')
            # Wait for images to replicate, this will take time.
            # Only wait if at least one region was replicated.
            time.sleep(300)

        for test_region, reg_info in self.test_region_results.items():
            credential = reg_info['credential']

            if reg_info['image_id']:
                try:
                    self._wait_on_image(
                        credential['access_key_id'],
                        credential['secret_access_key'],
                        reg_info['image_id'],
                        test_region
                    )
                except Exception as error:
                    self.status = FAILED
                    msg = 'Replicate to {0} region failed: {1}'.format(
                        test_region,
                        error
                    )
                    self.add_error_msg(msg)
                    self.log_callback.warning(msg)

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
                description = (
                    f'Image {image_id} replicated from {source_region} to '
                    f'{target_region} for tests execution in this region.'
                )
                new_image = client.copy_image(
                    Description=description,
                    Name=self.cloud_image_name,
                    SourceImageId=image_id,
                    SourceRegion=source_region,
                )
            else:
                new_image = {'ImageId': None}
        except Exception as e:
            raise MashTestPreparationException(
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
                raise MashTestPreparationException(
                    'The image with ID: {0} was not found.'.format(
                        image_id
                    )
                )

            if state == 'available':
                break
            elif state == 'failed':
                raise MashTestPreparationException(
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
