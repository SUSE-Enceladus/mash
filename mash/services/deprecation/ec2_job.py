# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

from ec2utils.ec2deprecateimg import EC2DeprecateImg

from mash.mash_exceptions import MashDeprecationException
from mash.services.deprecation.job import DeprecationJob
from mash.services.status_levels import SUCCESS


class EC2DeprecationJob(DeprecationJob):
    """
    Class for an EC2 deprecation job.
    """

    def __init__(
        self, id, provider, utctime, old_cloud_image_name,
        job_file=None, deprecation_regions=None
    ):
        super(EC2DeprecationJob, self).__init__(
            id, provider, utctime, job_file=job_file
        )
        self.credentials = None
        self.old_cloud_image_name = old_cloud_image_name
        self.job_file = job_file
        self.deprecation_regions = deprecation_regions

    def _deprecate(self):
        """
        Deprecate image in all target regions in each source region.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecation for the job.
            return

        for region_info in self.deprecation_regions:
            credential = self.credentials[region_info['account']]

            deprecator = EC2DeprecateImg(
                access_key=credential['access_key_id'],
                secret_key=credential['secret_access_key'],
                deprecation_image_name=self.old_cloud_image_name,
                replacement_image_name=self.cloud_image_name,
                verbose=False
            )

            for region in region_info['target_regions']:
                deprecator.set_region(region)
                try:
                    result = deprecator.deprecate_images()
                    if result is False:
                        raise Exception('No images to deprecate.')
                except Exception as error:
                    raise MashDeprecationException(
                        'Error deprecating image {0} in {1}. {2}'.format(
                            self.old_cloud_image_name, region, error
                        )
                    )
