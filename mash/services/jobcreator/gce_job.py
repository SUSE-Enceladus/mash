# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class GCEJob(BaseJob):
    """
    GCE job message class.
    """
    def __init__(
        self, accounts_info, cloud_data, job_id, cloud,
        requesting_user, last_service,
        utctime, image, cloud_image_name, image_description, distro,
        download_url, tests=None, conditions=None, instance_type=None,
        family=None, old_cloud_image_name=None, cleanup_images=True,
        cloud_architecture='x86_64', months_to_deletion=6,
        cloud_accounts=None, cloud_groups=None,
        notification_email=None, notification_type='single'
    ):
        self.family = family
        self.target_account_info = {}

        super(GCEJob, self).__init__(
            accounts_info, cloud_data, job_id, cloud,
            requesting_user, last_service, utctime, image,
            cloud_image_name, image_description, distro, download_url, tests,
            conditions, instance_type, old_cloud_image_name, cleanup_images,
            cloud_architecture, cloud_accounts, cloud_groups,
            notification_email, notification_type
        )

        self.months_to_deletion = months_to_deletion

    def _get_account_info(self):
        """
        Returns a dictionary of regions to accounts.

        Example: {
            'us-west1': {
                'account': 'acnt1',
                'bucket': 'images',
                'family': 'sles-15'
            }
        }
        """
        for account, info in self.accounts_info.items():
            region = self.cloud_accounts[account].get('region') or \
                info.get('region')

            bucket = self.cloud_accounts[account].get('bucket') or \
                info.get('bucket')

            self.target_account_info[region] = {
                'account': account,
                'bucket': bucket,
                'family': self.family
            }

    def get_deprecation_message(self):
        """
        Build deprecation job message.
        """
        deprecation_message = {
            'deprecation_job': {
                'cloud': self.cloud,
                'deprecation_accounts': self.get_deprecation_accounts(),
                'months_to_deletion': self.months_to_deletion
            }
        }
        deprecation_message['deprecation_job'].update(self.base_message)

        if self.old_cloud_image_name:
            deprecation_message['deprecation_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(deprecation_message)

    def get_deprecation_accounts(self):
        """
        Return list of deprecation account info.
        """
        deprecation_accounts = []

        for source_region, value in self.target_account_info.items():
            deprecation_accounts.append(value['account'])

        return deprecation_accounts

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'cloud': self.cloud
            }
        }
        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_message = {
            'replication_job': {
                'cloud': self.cloud
            }
        }
        replication_message['replication_job'].update(self.base_message)

        return JsonFormat.json_message(replication_message)

    def get_testing_regions(self):
        """
        Return a dictionary of target test regions.
        """
        test_regions = {}

        for source_region, value in self.target_account_info.items():
            test_regions[source_region] = value['account']

        return test_regions

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.
        """
        return self.target_account_info

    def post_init(self):
        """
        Post initialization method.
        """
        self._get_account_info()
