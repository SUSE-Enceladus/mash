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
        self, accounts_info, provider_data, job_id, provider,
        provider_accounts, provider_groups, requesting_user, last_service,
        utctime, image, cloud_image_name, image_description, distro,
        download_url, tests, conditions=None, instance_type=None, family=None,
        old_cloud_image_name=None, cleanup_images=True
    ):
        self.family = family
        self.target_account_info = {}

        super(GCEJob, self).__init__(
            accounts_info, provider_data, job_id, provider, provider_accounts,
            provider_groups, requesting_user, last_service, utctime, image,
            cloud_image_name, image_description, distro, download_url, tests,
            conditions, instance_type, old_cloud_image_name, cleanup_images
        )

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
        group_accounts = []
        accounts = {}

        # Get dictionary of account names to account dict
        for provider_account in self.provider_accounts:
            accounts[provider_account['name']] = provider_account

        # Get all accounts from all groups
        for group in self.provider_groups:
            group_accounts += self._get_accounts_in_group(
                group, self.requesting_user
            )

        # Add accounts from groups that don't already exist
        for account in group_accounts:
            if account not in accounts:
                accounts[account] = {}

        for account, info in accounts.items():
            region = info.get('region') or \
                self.accounts_info['accounts'][self.requesting_user][account]\
                    .get('region')

            bucket = info.get('bucket') or \
                self.accounts_info['accounts'][self.requesting_user][account] \
                    .get('bucket')

            self.target_account_info[region] = {
                'account': account,
                'bucket': bucket,
                'family': self.family
            }

    def get_deprecation_regions(self):
        """
        Return list of deprecation region info.

        """
        raise NotImplementedError('TODO')

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'provider': self.provider,
                'publish_regions': self.get_publisher_regions()
            }
        }
        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        return []  # No publishing in GCE

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_message = {
            'replication_job': {
                'provider': self.provider,
                'replication_source_regions':
                    self.get_replication_source_regions()
            }
        }
        replication_message['replication_job'].update(self.base_message)

        return JsonFormat.json_message(replication_message)

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.
        """
        return {}  # No replication in GCE

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
