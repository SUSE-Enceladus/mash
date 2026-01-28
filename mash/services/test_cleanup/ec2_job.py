# Copyright (c) 2024 SUSE LLC.  All rights reserved.
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

from mash.mash_exceptions import MashTestCleanupException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS
from mash.utils.ec2 import cleanup_ec2_image


class EC2TestCleanupJob(MashJob):
    """
    Class for an EC2 Cleanup job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.test_cleanup_regions = self.job_config['test_cleanup_regions']

        except KeyError as error:
            raise MashTestCleanupException(
                'EC2 Test cleanup job requires a(n) '
                f'{0} key in the job doc.'.format(error)
            )

    def run_job(self):
        """
        Clean up the images that where replicated for testing purposes by the
        test_preparation service.
        """
        self.status = SUCCESS

        # Get all account credentials in one request
        accounts = []
        region_accounts = {}
        for test_cleanup_region, reg_info in self.test_cleanup_regions.items():
            account = reg_info['account']
            if account not in accounts:
                accounts.append(account)
            if 'target_regions' in reg_info:
                for target_region in reg_info['target_regions']:
                    region_accounts[target_region] = account

        self.request_credentials(accounts)

        regions_to_cleanup = self.status_msg.get('test_replicated_regions', {})
        for region, image_id in regions_to_cleanup.items():
            account = region_accounts[region]
            credentials = self.credentials[account]

            cleanup_ec2_image(
                credentials['access_key_id'],
                credentials['secret_access_key'],
                self.log_callback,
                region,
                image_id=image_id
            )
