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
from mash.services.api.utils.users import get_user_by_id
from mash.services.api.models import EC2Group, EC2Region, EC2Account
from mash.utils.mash_utils import handle_request


def get_ec2_group(name, user_id):
    """
    Retrieve EC2 group for user.

    If group does not exist raise exception.
    """
    group = EC2Group.query.filter_by(name=name, user_id=user_id).first()

    if not group:
        raise MashDBException(
            'Group {name} does not exist'.format(name=name)
        )

    return group


def _get_or_create_ec2_group(name, user_id):
    """
    Retrieve EC2 group for user.

    If group does not exist create it.
    """
    group = EC2Group.query.filter_by(name=name, user_id=user_id).first()

    if not group:
        group = EC2Group(
            name=name,
            user_id=user_id
        )
        db.session.add(group)

    return group


def create_ec2_region(region_name, helper_image, account):
    """
    Create new EC2 region for EC2 account.
    """
    region = EC2Region(
        name=region_name,
        helper_image=helper_image,
        account=account
    )
    db.session.add(region)
    return region


def create_ec2_account(
    user_id,
    account_name,
    partition,
    region_name,
    credentials,
    subnet,
    group_name,
    additional_regions
):
    """
    Create a new EC2 account for user.

    Create a new group and additional regions if necessary.
    """
    data = {
        'cloud': 'ec2',
        'account_name': account_name,
        'requesting_user': user_id,
        'credentials': credentials
    }

    account = EC2Account(
        name=account_name,
        partition=partition,
        region=region_name,
        subnet=subnet,
        user_id=user_id
    )

    if group_name:
        group = _get_or_create_ec2_group(group_name, user_id)
        account.group = group

    if additional_regions:
        for additional_region in additional_regions:
            create_ec2_region(
                additional_region['name'],
                additional_region['helper_image'],
                account
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


def get_ec2_accounts(user_id):
    """
    Retrieve all EC2 accounts for user.
    """
    user = get_user_by_id(user_id)
    return user.ec2_accounts


def get_ec2_account(name, user_id):
    """
    Get EC2 account for given user.
    """
    try:
        ec2_account = EC2Account.query.filter_by(
            name=name, user_id=user_id
        ).one()
    except Exception:
        raise MashDBException(
            'EC2 account {name} does not exist'.format(name=name)
        )

    return ec2_account


def delete_ec2_account(name, user_id):
    """
    Delete EC2 account for user.
    """
    data = {
        'cloud': 'ec2',
        'account_name': name,
        'requesting_user': user_id
    }

    ec2_account = get_ec2_account(name, user_id)

    if ec2_account:
        try:
            db.session.delete(ec2_account)
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


def update_ec2_account(
    account_name,
    user_id,
    additional_regions=None,
    credentials=None,
    group=None,
    region=None,
    subnet=None
):
    """
    Update an existing EC2 account.
    """
    ec2_account = get_ec2_account(account_name, user_id)

    if not ec2_account:
        return None

    if credentials:
        data = {
            'cloud': 'ec2',
            'account_name': account_name,
            'requesting_user': user_id,
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

    if group:
        ec2_account.group = _get_or_create_ec2_group(group, user_id)

    if additional_regions:
        for additional_region in additional_regions:
            create_ec2_region(
                additional_region['name'],
                additional_region['helper_image'],
                ec2_account
            )

    if region:
        ec2_account.region = region

    if subnet:
        ec2_account.subnet = subnet

    try:
        db.session.add(ec2_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return ec2_account
