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


def create_oci_account(
    user_id,
    data
):
    """
    Create a new OCI account for user.
    """
    data['user_id'] = user_id

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'oci_accounts/',
        'post',
        job_data=data
    )

    return response.json()


def get_oci_accounts(user_id):
    """
    Retrieve all OCI accounts for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'oci_accounts/list/{user}'.format(user=user_id),
        'get'
    )

    return response.json()


def get_oci_account(name, user_id):
    """
    Get OCI account for given user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'oci_accounts/',
        'get',
        job_data={'name': name, 'user_id': user_id}
    )

    account = response.json()

    if not account:
        raise MashException(
            'OCI account {account} not found. '.format(
                account=name
            )
        )

    return account


def delete_oci_account(name, user_id):
    """
    Delete OCI account for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'oci_accounts/',
        'delete',
        job_data={'name': name, 'user_id': user_id}
    )

    return response.json()['rows_deleted']


def update_oci_account(
    account_name,
    user_id,
    data
):
    """
    Update OCI account for user.
    """
    data['account_name'] = account_name
    data['user_id'] = user_id

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'oci_accounts/',
        'put',
        job_data=data
    )

    return response.json()
