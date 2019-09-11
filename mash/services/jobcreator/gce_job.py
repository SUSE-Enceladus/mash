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
        self.guest_os_features = self.kwargs.get('guest_os_features')

    def get_credentials_message(self):
        """
        Build credentials job message.
        """
        accounts = []
        for source_region, value in self.target_account_info.items():
            accounts.append(value['account'])

            testing_account = value.get('testing_account')
            if testing_account and testing_account not in accounts:
                accounts.append(testing_account)

        credentials_message = {
            'credentials_job': {
                'cloud': self.cloud,
                'cloud_accounts': accounts,
                'requesting_user': self.requesting_user
            }
        }
        credentials_message['credentials_job'].update(self.base_message)

        return credentials_message

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
                'is_publishing_account': value['is_publishing_account']
            }

            if value.get('testing_account'):
                test_regions[source_region]['testing_account'] = value['testing_account']

        return test_regions

    def get_uploader_message(self):
        """
        Build uploader job message.
        """
        uploader_message = {
            'uploader_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'image_description': self.image_description,
                'family': self.family,
                'guest_os_features': self.guest_os_features,
                'target_regions': self.get_uploader_regions()
            }
        }
        uploader_message['uploader_job'].update(self.base_message)

        if self.cloud_architecture:
            uploader_message['uploader_job']['cloud_architecture'] = \
                self.cloud_architecture

        return JsonFormat.json_message(uploader_message)

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.
        """
        return self.target_account_info
