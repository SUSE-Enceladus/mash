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


class AzureJob(BaseJob):
    """
    Azure job message class.
    """
    def __init__(
        self, accounts_info, provider_data, job_id, provider,
        provider_accounts, provider_groups, requesting_user, last_service,
        utctime, image, cloud_image_name, image_description, distro,
        download_url, tests, offer_id, publisher_id, sku, emails, label,
        conditions=None, instance_type=None, old_cloud_image_name=None,
        cleanup_images=True, cloud_architecture='x86_64', version_key=None
    ):
        self.target_account_info = {}

        super(AzureJob, self).__init__(
            accounts_info, provider_data, job_id, provider, provider_accounts,
            provider_groups, requesting_user, last_service, utctime, image,
            cloud_image_name, image_description, distro, download_url, tests,
            conditions, instance_type, old_cloud_image_name, cleanup_images,
            cloud_architecture
        )

        self.emails = emails
        self.label = label
        self.offer_id = offer_id
        self.publisher_id = publisher_id
        self.sku = sku
        self.version_key = version_key

    def _get_account_info(self):
        """
        Returns a dictionary of accounts and regions.

        Example: {
            'southcentralus': {
                'account': 'acnt1',
                'source_resource_group': 'rg-1',
                'source_container': 'container1',
                'source_storage_account': 'sa1',
                'destination_resource_group': 'rg-2',
                'destination_container': 'container2',
                'destination_storage_account': 'sa2'
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
            source_resource_group = info.get('source_resource_group') or \
                self._get_account_value(account, 'source_resource_group')
            source_container = info.get('source_container') or \
                self._get_account_value(account, 'source_container')
            source_storage_account = info.get('source_storage_account') or \
                self._get_account_value(account, 'source_storage_account')
            destination_resource_group = info.get(
                'destination_resource_group'
            ) or self._get_account_value(
                account, 'destination_resource_group'
            )
            destination_container = info.get(
                'destination_container'
            ) or self._get_account_value(
                account, 'destination_container'
            )
            destination_storage_account = info.get(
                'destination_storage_account'
            ) or self._get_account_value(
                account, 'destination_storage_account'
            )

            self.target_account_info[region] = {
                'account': account,
                'source_resource_group': source_resource_group,
                'source_container': source_container,
                'source_storage_account': source_storage_account,
                'destination_resource_group': destination_resource_group,
                'destination_container': destination_container,
                'destination_storage_account': destination_storage_account
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
        publisher_message = {
            'publisher_job': {
                'emails': self.emails,
                'image_description': self.image_description,
                'label': self.label,
                'offer_id': self.offer_id,
                'provider': self.provider,
                'publish_regions': self.get_publisher_regions(),
                'publisher_id': self.publisher_id,
                'sku': self.sku
            }
        }

        if self.version_key:
            publisher_message['publisher_job']['version_key'] = \
                self.version_key

        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        publish_regions = []

        for source_region, value in self.target_account_info.items():
            publish_regions.append({
                'account': value['account'],
                'destination_container': value['destination_container'],
                'destination_resource_group':
                    value['destination_resource_group'],
                'destination_storage_account':
                    value['destination_storage_account']
            })

        return publish_regions

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_message = {
            'replication_job': {
                'cleanup_images': self.cleanup_images,
                'image_description': self.image_description,
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
        return self.target_account_info

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
            target_regions[source_region] = {}
            target_regions[source_region]['account'] = value['account']
            target_regions[source_region]['container'] = \
                value['source_container']
            target_regions[source_region]['storage_account'] = \
                value['source_storage_account']
            target_regions[source_region]['resource_group'] = \
                value['source_resource_group']

        return target_regions

    def post_init(self):
        """
        Post initialization method.
        """
        self._get_account_info()
