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

from mash.services.credentials.base_account import BaseAccount


class AzureAccount(BaseAccount):
    """
    Azure cloud account.

    Handles management of accounts in the json accounts file.
    """
    def __init__(self, message):
        super(AzureAccount, self).__init__(
            message['account_name'],
            message['cloud'], message['requesting_user'],
            group_name=message.get('group')
        )
        self.region = message['region']
        self.source_container = message['source_container']
        self.source_resource_group = message['source_resource_group']
        self.source_storage_account = message['source_storage_account']
        self.destination_container = message['destination_container']
        self.destination_resource_group = \
            message['destination_resource_group']
        self.destination_storage_account = \
            message['destination_storage_account']

    def add_account(self, accounts_file):
        """
        Add new account to the accounts file.

        Update or add group if provided.
        """
        account_info = {
            'region': self.region,
            'source_container': self.source_container,
            'source_resource_group': self.source_resource_group,
            'source_storage_account': self.source_storage_account,
            'destination_container': self.destination_container,
            'destination_resource_group': self.destination_resource_group,
            'destination_storage_account': self.destination_storage_account
        }

        accounts = accounts_file[self.cloud]['accounts'].get(self.requesting_user)

        if accounts:
            accounts[self.account_name] = account_info
        else:
            accounts_file[self.cloud]['accounts'][self.requesting_user] = {
                self.account_name: account_info
            }

        # Add group if necessary
        if self.group_name:
            self.add_account_to_group(accounts_file)
