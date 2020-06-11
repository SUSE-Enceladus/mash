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

from ec2imgutils.ec2deprecateimg import EC2DeprecateImg

from mash.mash_exceptions import MashDeprecateException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS


class EC2DeprecateJob(MashJob):
    """
    Class for an EC2 deprecate job.
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

    def run_job(self):
        """
        Deprecate image in all target regions in each source region.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecate for the job.
            return

        # Get all account credentials in one request
        accounts = []
        for region_info in self.deprecate_regions:
            accounts.append(region_info['account'])

        self.request_credentials(accounts)
        cloud_image_name = self.source_regions['cloud_image_name']

        for region_info in self.deprecate_regions:
            credential = self.credentials[region_info['account']]

            deprecator = EC2DeprecateImg(
                access_key=credential['access_key_id'],
                secret_key=credential['secret_access_key'],
                deprecation_image_name=self.old_cloud_image_name,
                replacement_image_name=cloud_image_name,
                log_callback=self.log_callback
            )

            for region in region_info['target_regions']:
                deprecator.set_region(region)
                try:
                    result = deprecator.deprecate_images()
                    if result is False:
                        self.log_callback.warning(
                            'Unable to deprecate image in {region}, '
                            'no image found.'.format(region=region)
                        )
                except Exception as error:
                    raise MashDeprecateException(
                        'Error deprecating image {0} in {1}. {2}'.format(
                            self.old_cloud_image_name, region, error
                        )
                    )
