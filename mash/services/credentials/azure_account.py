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
    Azure provider account.

    Handles management of accounts in the json accounts file.
    """
    def __init__(self, message):
        super(AzureAccount, self).__init__(
            message['account_name'],
            message['provider'], message['requesting_user'],
            group_name=message.get('group')
        )
        self.container_name = message['container_name']
        self.region = message['region']
        self.resource_group = message['resource_group']
        self.storage_account = message['storage_account']

    def add_account(self, accounts_file):
        """
        Add new account to the accounts file.

        Update or add group if provided.
        """
        account_info = {
            'container_name': self.container_name,
            'region': self.region,
            'resource_group': self.resource_group,
            'storage_account': self.storage_account
        }

        accounts = accounts_file[self.provider]['accounts'].get(self.requesting_user)

        if accounts:
            accounts[self.account_name] = account_info
        else:
            accounts_file[self.provider]['accounts'][self.requesting_user] = {
                self.account_name: account_info
            }

        # Add group if necessary
        if self.group_name:
            self.add_account_to_group(accounts_file)
