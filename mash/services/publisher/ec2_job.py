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

import re

from itertools import repeat
from ec2utils.ec2publishimg import EC2PublishImage

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
        self.share_with = self.validate_share_with(share_with)

    def _publish(self):
        """
        Publish image and update status.
        """
        for region_info in self.publish_regions:
            creds = self.credentials[region_info['account']]

            publisher = EC2PublishImage(
                access_key=creds['access_key_id'],
                allow_copy=self.allow_copy,
                secret_key=creds['secret_access_key'],
                verbose=False,
                visibility=self.share_with,
            )

            for region in region_info['target_regions']:
                publisher.set_region(region)
                publisher.image_id = self.source_regions[region]
                try:
                    publisher.publish_images()
                except Exception as error:
                    raise MashPublisherException(
                        'An error publishing image {0} in {1}. {2}'.format(
                            self.source_regions[region], region, error
                        )
                    )

        self.status = SUCCESS

    def validate_account_numbers(self, share_with):
        """
        Validate the share_with attr is a comma separated list of accounts.
        """
        accounts = list(filter(None, share_with.split(',')))
        if accounts:
            return all(map(re.match, repeat('^\d{12}$'), accounts))
        return False

    def validate_share_with(self, share_with):
        """
        Validate share with is all, none or a comma separated list of accounts.
        """
        if share_with:
            error_msg = 'Share with must be "all", "none", or ' \
                'comma separated list of 12 digit AWS account numbers.'

            try:
                share_with = share_with.lower()
            except Exception:
                raise MashPublisherException(error_msg)

            if share_with not in ('all', 'none') \
                    and not self.validate_account_numbers(share_with):
                raise MashPublisherException(error_msg)

        return share_with
