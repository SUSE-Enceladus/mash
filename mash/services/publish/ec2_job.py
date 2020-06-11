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

from ec2imgutils.ec2publishimg import EC2PublishImage

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS


class EC2PublishJob(MashJob):
    """
    Class for an EC2 publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.publish_regions = self.job_config['publish_regions']
        except KeyError as error:
            raise MashPublishException(
                'EC2 publish Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.allow_copy = self.job_config.get('allow_copy', 'none')
        self.share_with = self.job_config.get('share_with', 'all')

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        # Get all account credentials in one request
        accounts = []
        for region_info in self.publish_regions:
            accounts.append(region_info['account'])

        self.request_credentials(accounts)
        cloud_image_name = self.source_regions['cloud_image_name']

        for region_info in self.publish_regions:
            creds = self.credentials[region_info['account']]

            publish = EC2PublishImage(
                access_key=creds['access_key_id'],
                allow_copy=self.allow_copy,
                image_name=cloud_image_name,
                secret_key=creds['secret_access_key'],
                visibility=self.share_with,
                log_callback=self.log_callback
            )

            for region in region_info['target_regions']:
                publish.set_region(region)
                try:
                    publish.publish_images()
                except Exception as error:
                    raise MashPublishException(
                        'An error publishing image {0} in {1}. {2}'.format(
                            cloud_image_name, region, error
                        )
                    )
