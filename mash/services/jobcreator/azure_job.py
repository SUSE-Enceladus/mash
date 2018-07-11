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

from mash.services.jobcreator.base_job import BaseJob


class AzureJob(BaseJob):
    """
    Azure job message class.
    """
    def __init__(
        self, job_id, accounts_info, provider_data, provider,
        provider_accounts, provider_groups, requesting_user, last_service,
        utctime, image, cloud_image_name, old_cloud_image_name, project,
        image_description, distro, tests, conditions=None,
        instance_type=None
    ):
        self.target_account_info = {}

        super(AzureJob, self).__init__(
            job_id, accounts_info, provider_data, provider, provider_accounts,
            provider_groups, requesting_user, last_service, utctime, image,
            cloud_image_name, old_cloud_image_name, project,
            image_description, distro, tests, conditions, instance_type
        )

    def _get_account_info(self):
        """
        Returns a dictionary of accounts and regions.

        Example: {
            'southcentralus': {
                'account': 'acnt1',
                'resource_group': 'rg-1',
                'container_name': 'container1,
                'storage_account': 'sa1'
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
                self._get_account_value(account, 'region')
            resource_group = info.get('resource_group') or \
                self._get_account_value(account, 'resource_group')
            container_name = info.get('container_name') or \
                self._get_account_value(account, 'container_name')
            storage_account = info.get('storage_account') or \
                self._get_account_value(account, 'storage_account')

            self.target_account_info[region] = {
                'account': account,
                'resource_group': resource_group,
                'container_name': container_name,
                'storage_account': storage_account
            }

    def _get_account_value(self, account, key):
        """
        Return the value for the provided account key from accounts file.
        """
        return self.accounts_info['accounts'][self.requesting_user][account][key]

    def get_deprecation_regions(self):
        """
        Return list of deprecation region info.

        """
        raise NotImplementedError('TODO')

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        raise NotImplementedError('TODO')

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        raise NotImplementedError('TODO')

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.
        """
        raise NotImplementedError('TODO')

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
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[source_region] = value

        return target_regions

    def post_init(self):
        """
        Post initialization method.
        """
        self._get_account_info()
