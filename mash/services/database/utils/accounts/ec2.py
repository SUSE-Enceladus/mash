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
from sqlalchemy.orm.exc import NoResultFound

from mash.services.database.extensions import db
from mash.services.database.utils.users import get_user_by_id
from mash.services.database.models import (
    EC2Group,
    EC2Region,
    EC2Account,
    EC2Subnet
)
from mash.utils.mash_utils import handle_request
from mash.mash_exceptions import MashDBException


def get_accounts_in_ec2_group(name, user_id):
    """
    Retrieve EC2 group for user.

    If group does not exist raise exception.
    """
    try:
        group = EC2Group.query.filter_by(name=name, user_id=user_id).one()
        accounts = group.accounts
    except NoResultFound:
        raise MashDBException('Group {group} not found.'.format(group=name))

    return accounts


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


def create_new_ec2_region(region_name, helper_image, account):
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


def create_new_ec2_subnet(region, subnet, account):
    """
    Creates a new EC2 subnet
    """
    new_subnet = EC2Subnet(
        region=region,
        subnet=subnet,
        account=account
    )
    db.session.add(new_subnet)
    return new_subnet


def create_new_ec2_account(
    user_id,
    account_name,
    partition,
    region_name,
    credentials,
    subnets,
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
        user_id=user_id
    )

    if group_name:
        group = _get_or_create_ec2_group(group_name, user_id)
        account.group = group

    if additional_regions:
        for additional_region in additional_regions:
            create_new_ec2_region(
                additional_region['name'],
                additional_region['helper_image'],
                account
            )

    if subnets:
        for subnet in subnets:
            create_new_ec2_subnet(
                region=subnet['region'],
                subnet=subnet['subnet'],
                account=account
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


def get_ec2_account_for_user(name, user_id):
    """
    Get EC2 account for given user.
    """
    try:
        ec2_account = EC2Account.query.filter_by(
            name=name,
            user_id=user_id
        ).one()
    except NoResultFound:
        ec2_account = None

    return ec2_account


def delete_ec2_account_for_user(name, user_id):
    """
    Delete EC2 account for user.
    """
    data = {
        'cloud': 'ec2',
        'account_name': name,
        'requesting_user': user_id
    }

    ec2_account = get_ec2_account_for_user(name, user_id)

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


def update_ec2_account_for_user(
    account_name,
    user_id,
    additional_regions=None,
    credentials=None,
    group=None,
    region=None,
    subnets=None
):
    """
    Update an existing EC2 account.
    """
    ec2_account = get_ec2_account_for_user(account_name, user_id)

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
            create_new_ec2_region(
                additional_region['name'],
                additional_region['helper_image'],
                ec2_account
            )

    if region:
        ec2_account.region = region

    if subnets:
        for subnet in subnets:
            create_new_ec2_subnet(
                region=subnet['region'],
                subnet=subnet['subnet'],
                account=ec2_account
            )

    try:
        db.session.add(ec2_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return ec2_account
