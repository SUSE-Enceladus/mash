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

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class GCEJob(BaseJob):
    """
    GCE job message class.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        self.family = self.kwargs.get('family')
        self.months_to_deletion = self.kwargs.get(
            'months_to_deletion', 6
        )

    def get_account_info(self):
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
            region = self.cloud_accounts[account].get(
                'region'
            ) or info.get('region')

            bucket = self.cloud_accounts[account].get(
                'bucket'
            ) or info.get('bucket')

            testing_account = info.get('testing_account')
            is_publishing_account = info.get('is_publishing_account')

            if is_publishing_account and not self.family:
                raise MashJobCreatorException(
                    'Jobs using a GCE publishing account require a family.'
                )

            if is_publishing_account and not testing_account:
                raise MashJobCreatorException(
                    'Jobs using a GCE publishing account require'
                    ' the use of a testing account.'
                )

            self.target_account_info[region] = {
                'account': account,
                'bucket': bucket,
                'family': self.family,
                'testing_account': testing_account,
                'is_publishing_account': is_publishing_account
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
            test_regions[source_region] = {
                'account': value['account'],
                'testing_account': value['testing_account'],
                'is_publishing_account': value['is_publishing_account']
            }

        return test_regions

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.
        """
        return self.target_account_info
