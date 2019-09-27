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

from flask import current_app

from mash.mash_exceptions import MashDBException
from mash.services.api.extensions import db
from mash.services.api.utils.users import get_user_by_username
from mash.services.api.models import AzureAccount, User
from mash.utils.mash_utils import handle_request


def create_azure_account(
    username,
    account_name,
    region_name,
    credentials,
    source_container,
    source_resource_group,
    source_storage_account,
    destination_container,
    destination_resource_group,
    destination_storage_account
):
    """
    Create a new Azure account for user.
    """
    data = {
        'cloud': 'azure',
        'account_name': account_name,
        'requesting_user': username,
        'credentials': credentials
    }

    user = get_user_by_username(username)

    account = AzureAccount(
        name=account_name,
        region=region_name,
        source_container=source_container,
        source_resource_group=source_resource_group,
        source_storage_account=source_storage_account,
        destination_container=destination_container,
        destination_resource_group=destination_resource_group,
        destination_storage_account=destination_storage_account,
        user_id=user.id
    )

    try:
        handle_request(
            current_app.config['CREDENTIALS_URL'],
            'credentials/',
            'post',
            job_data=data
        )
        db.session.add(account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return account


def get_azure_account(name, username):
    """
    Get Azure account for given user.
    """
    azure_account = AzureAccount.query.filter(
        User.username == username
    ).filter_by(name=name).first()

    return azure_account


def get_azure_accounts(username):
    """
    Retrieve all Azure accounts for user.
    """
    user = get_user_by_username(username)
    return user.azure_accounts


def get_azure_account_by_id(name, user_id):
    """
    Get Azure account for given user.
    """
    try:
        azure_account = AzureAccount.query.filter_by(
            name=name, user_id=user_id
        ).one()
    except Exception:
        raise MashDBException(
            'Azure account {name} does not exist'.format(name=name)
        )

    return azure_account


def delete_azure_account(name, username):
    """
    Delete Azure account for user.
    """
    data = {
        'cloud': 'azure',
        'account_name': name,
        'requesting_user': username
    }

    azure_account = get_azure_account(name, username)

    if azure_account:
        try:
            db.session.delete(azure_account)
            db.session.commit()
            handle_request(
                current_app.config['CREDENTIALS_URL'],
                'credentials/',
                'delete',
                job_data=data
            )
        except Exception:
            db.session.rollback()
            raise
        else:
            return 1
    else:
        return 0


def update_azure_account(
    account_name,
    username,
    region=None,
    credentials=None,
    source_container=None,
    source_resource_group=None,
    source_storage_account=None,
    destination_container=None,
    destination_resource_group=None,
    destination_storage_account=None
):
    """
    Update Azure account for user.
    """
    account = get_azure_account(account_name, username)

    if not account:
        return None

    if credentials:
        data = {
            'cloud': 'azure',
            'account_name': account_name,
            'requesting_user': username,
            'credentials': credentials
        }

        try:
            handle_request(
                current_app.config['CREDENTIALS_URL'],
                'credentials/',
                'post',
                job_data=data
            )
        except Exception:
            raise

    if region:
        account.region = region

    if source_container:
        account.source_container = source_container

    if source_resource_group:
        account.source_resource_group = source_resource_group

    if source_storage_account:
        account.source_storage_account = source_storage_account

    if destination_container:
        account.destination_container = destination_container

    if destination_resource_group:
        account.destination_resource_group = destination_resource_group

    if destination_storage_account:
        account.destination_storage_account = destination_storage_account

    try:
        db.session.add(account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return account
