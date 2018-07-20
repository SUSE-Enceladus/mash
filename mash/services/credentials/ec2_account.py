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


class EC2Account(BaseAccount):
    """
    EC2 provider account.

    Handles management of accounts in the json accounts file.
    """
    def __init__(self, message):
        super(EC2Account, self).__init__(
            message['account_name'],
            message['provider'], message['requesting_user'],
            group_name=message.get('group')
        )
        self.additional_regions = message.get('additional_regions')
        self.partition = message['partition']

    def add_account(self, accounts_file):
        """
        Add new account to the accounts file.

        Update or add group if provided.
        """
        accounts = accounts_file[self.provider]['accounts'].get(self.requesting_user)

        if accounts:
            accounts[self.account_name] = self.partition
        else:
            accounts_file[self.provider]['accounts'][self.requesting_user] = {
                self.account_name: {
                    'additional_regions': self.additional_regions,
                    'partition': self.partition
                }
            }

        # Add group if necessary
        if self.group_name:
            self.add_account_to_group(accounts_file)
