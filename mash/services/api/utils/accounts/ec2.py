# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

from flask import current_app

from mash.utils.mash_utils import handle_request
from mash.mash_exceptions import MashException


def get_accounts_in_ec2_group(group_name, user_id):
    """
    Get an EC2 group for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/group_accounts',
        'get',
        job_data={'user_id': user_id, 'group_name': group_name}
    )

    return response.json()


def create_ec2_account(user_id, data):
    """
    Create a new EC2 account for user.
    """
    data['user_id'] = user_id

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/',
        'post',
        job_data=data
    )

    return response.json()


def get_ec2_accounts(user_id):
    """
    Retrieve all EC2 accounts for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/list/{user}'.format(user=user_id),
        'get'
    )

    return response.json()


def get_ec2_account(name, user_id):
    """
    Get EC2 account for given user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/',
        'get',
        job_data={'name': name, 'user_id': user_id}
    )

    account = response.json()

    if not account:
        raise MashException(
            'EC2 account {account} not found. '.format(
                account=name
            )
        )

    return account


def delete_ec2_account(name, user_id):
    """
    Delete EC2 account for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/',
        'delete',
        job_data={'name': name, 'user_id': user_id}
    )

    return response.json()['rows_deleted']


def update_ec2_account(account_name, user_id, data):
    """
    Update EC2 account for user.
    """
    data['account_name'] = account_name
    data['user_id'] = user_id

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'ec2_accounts/',
        'put',
        job_data=data
    )

    return response.json()
