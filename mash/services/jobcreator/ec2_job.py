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

import random

from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class EC2Job(BaseJob):
    """
    Base job message class.

    Handles incoming job requests.
    """
    def __init__(
        self, accounts_info, provider_data, job_id, provider,
        provider_accounts, provider_groups, requesting_user, last_service,
        utctime, image, cloud_image_name, old_cloud_image_name,
        image_description, distro, download_url, tests,
        allow_copy=False, conditions=None, instance_type=None,
        share_with='none'
    ):
        self.share_with = share_with
        self.allow_copy = allow_copy
        self.target_account_info = {}

        super(EC2Job, self).__init__(
            accounts_info, provider_data, job_id, provider, provider_accounts,
            provider_groups, requesting_user, last_service, utctime, image,
            cloud_image_name, old_cloud_image_name,
            image_description, distro, download_url, tests, conditions,
            instance_type
        )

    def _get_account_info(self):
        """
        Returns a dictionary of accounts and regions.

        The provided target_regions dictionary may contain a list
        of groups and accounts. An account may have a list of regions.

        If regions are not provided for an account the default list
        of all regions available is used.

        Example: {
            'us-east-1': {
                'account': 'acnt1',
                'target_regions': ['us-east-2', 'us-west-1', 'us-west-2']
            }
        }
        """
        group_accounts = []
        accounts = {}

        # Get dictionary of account names to target regions
        for provider_account in self.provider_accounts:
            accounts[provider_account['name']] = \
                provider_account['target_regions']

        helper_images = self.provider_data.get('helper_images')

        # Get all accounts from all groups
        for group in self.provider_groups:
            group_accounts += self._get_accounts_in_group(
                group, self.requesting_user
            )

        # Add accounts from groups that don't already exist
        for account in group_accounts:
            if account not in accounts:
                accounts[account] = None

        for account, target_regions in accounts.items():
            if not target_regions:
                # Get default list of all available regions for account
                target_regions = self._get_regions_for_account(
                    account, self.requesting_user
                )

                # Add additional regions for account
                additional_regions = \
                    self.accounts_info['accounts'][self.requesting_user][account]\
                        .get('additional_regions')

                if additional_regions:
                    for region in additional_regions:
                        helper_images[region['name']] = region['helper_image']
                        target_regions.append(region['name'])

            # A random region is selected as source region.
            index = random.randint(0, len(target_regions) - 1)
            target = target_regions[index]
            self.target_account_info[target] = {
                'account': account,
                'target_regions': target_regions,
                'helper_image': helper_images[target]
            }

    def _get_regions_for_account(self, account, user):
        """
        Return a list of regions based on account name.
        """
        regions_key = self.accounts_info['accounts'][user][account]['partition']
        return self.provider_data['regions'][regions_key]

    def _get_target_regions_list(self):
        """
        Return list of region info.
        """
        regions = []

        for source_region, value in self.target_account_info.items():
            regions.append(value)

        return regions

    def get_deprecation_regions(self):
        """
        Return list of deprecation region info.

        """
        return self._get_target_regions_list()

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'provider': self.provider,
                'allow_copy': self.allow_copy,
                'share_with': self.share_with,
                'publish_regions': self.get_publisher_regions()
            }
        }
        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        return self._get_target_regions_list()

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.
        """
        replication_source_regions = {}

        for source_region, value in self.target_account_info.items():
            replication_source_regions[source_region] = {
                'account': value['account'],
                'target_regions': value['target_regions']
            }

        return replication_source_regions

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
            target_regions[source_region] = {
                'account': value['account'],
                'helper_image': value['helper_image']
            }

        return target_regions

    def post_init(self):
        """
        Post initialization method.
        """
        self._get_account_info()
