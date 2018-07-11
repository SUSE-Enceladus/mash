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


class BaseAccount(object):
    """
    Base provider account.
    """
    def __init__(
        self, account_name, partition, provider,
        requesting_user, group_name=None
    ):
        self.account_name = account_name
        self.group_name = group_name
        self.partition = partition
        self.provider = provider
        self.requesting_user = requesting_user

    def add_account(self, accounts_file):
        """
        Add new account to the accounts file.

        Update or add group if provided.
        """
        pass

    def add_account_to_group(self, accounts):
        """
        Add the account to the group for the requesting user.

        If the group does not exist create it with the new account.
        """
        groups = accounts[self.provider]['groups'].get(self.requesting_user)

        if groups:
            group = groups.get(self.group_name)

            if not group:
                groups[self.group_name] = [self.account_name]
            elif self.account_name not in group:
                # Allow for account updates, don't append multiple times.
                group.append(self.account_name)
        else:
            accounts[self.provider]['groups'][self.requesting_user] = {
                self.group_name: [self.account_name]
            }
