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

from mash.csp import CSP

from mash.mash_exceptions import MashCredentialsException


def add_account_to_db(message, accounts):
    """
    Add account to accounts database based on message data.
    """
    cloud = message['cloud']
    requesting_user = message['requesting_user']
    account_name = message['account_name']
    group_name = message.get('group')

    if cloud == CSP.ec2:
        account_info = {
            'additional_regions': message.get('additional_regions'),
            'partition': message['partition'],
            'region': message.get('region')
        }
    elif cloud == CSP.azure:
        account_info = {
            'region': message['region'],
            'source_container': message['source_container'],
            'source_resource_group': message['source_resource_group'],
            'source_storage_account': message['source_storage_account'],
            'destination_container': message['destination_container'],
            'destination_resource_group': message['destination_resource_group'],
            'destination_storage_account': message['destination_storage_account']
        }
    elif cloud == CSP.gce:
        account_info = {
            'bucket': message['bucket'],
            'region': message['region'],
            'testing_account': message.get('testing_account')
        }
    else:
        raise MashCredentialsException(
            'CSP {0} is not supported.'.format(cloud)
        )

    user_data = accounts[cloud]['accounts'].get(requesting_user)

    if user_data:
        user_data[account_name] = account_info
    else:
        accounts[cloud]['accounts'][requesting_user] = {
            account_name: account_info
        }

    # Add group if necessary
    if group_name:
        accounts = add_account_to_group(
            accounts, cloud, requesting_user, group_name, account_name
        )

    return accounts


def delete_account_from_db(accounts, requesting_user, account_name, cloud):
    """Delete account for requesting user."""
    del accounts[cloud]['accounts'][requesting_user][account_name]
    return accounts


def add_account_to_group(
    accounts, cloud, requesting_user, group_name, account_name
):
    """
    Add the account to the group for the requesting user.

    If the group does not exist create it with the new account.
    """
    groups = accounts[cloud]['groups'].get(requesting_user)

    if groups:
        group = groups.get(group_name)

        if not group:
            groups[group_name] = [account_name]
        elif account_name not in group:
            # Allow for account updates, don't append multiple times.
            group.append(account_name)
    else:
        accounts[cloud]['groups'][requesting_user] = {
            group_name: [account_name]
        }

    return accounts


def remove_account_from_groups(
    accounts, account_name, cloud, requesting_user
):
    """Remove account from any groups it currently exists for user."""
    groups = accounts[cloud]['groups'][requesting_user]

    for group, account_names in groups.items():
        if account_name in account_names:
            account_names.remove(account_name)

    return accounts
