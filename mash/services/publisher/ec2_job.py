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

from ec2imgutils.ec2publishimg import EC2PublishImage

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher.job import PublisherJob
from mash.services.status_levels import SUCCESS


class EC2PublisherJob(PublisherJob):
    """
    Class for an EC2 publishing job.
    """

    def __init__(
        self, id, provider, publish_regions, utctime,
        allow_copy=False, job_file=None, share_with='all'
    ):
        super(EC2PublisherJob, self).__init__(
            id, provider, publish_regions, utctime, job_file=job_file
        )
        self.allow_copy = allow_copy
        self.share_with = share_with

    def _publish(self):
        """
        Publish image and update status.
        """
        for region_info in self.publish_regions:
            creds = self.credentials[region_info['account']]

            publisher = EC2PublishImage(
                access_key=creds['access_key_id'],
                allow_copy=self.allow_copy,
                image_name=self.cloud_image_name,
                secret_key=creds['secret_access_key'],
                verbose=False,
                visibility=self.share_with,
            )

            for region in region_info['target_regions']:
                publisher.set_region(region)
                try:
                    publisher.publish_images()
                except Exception as error:
                    raise MashPublisherException(
                        'An error publishing image {0} in {1}. {2}'.format(
                            self.cloud_image_name, region, error
                        )
                    )

        self.status = SUCCESS
