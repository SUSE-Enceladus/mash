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

import copy

from flask import current_app
from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashDBException, MashJobException
from mash.services.api.extensions import db
from mash.services.api.models import (
    EC2Account,
    EC2Group,
    EC2Region,
    User
)
from mash.utils.mash_utils import handle_request


def add_user(username, email, password):
    """
    Add new user to database and set password hash.

    If the user or email exists return None.
    """
    user = User(
        username=username,
        email=email
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None

    return user


def verify_login(username, password):
    """
    Compare password hashes.

    If hashes match the user is authenticated
    and user instance is returned.
    """
    user = get_user_by_username(username)

    if user and user.check_password(password):
        return user
    else:
        return None


def get_user_by_username(username):
    """
    Retrieve user from database if a match exists.

    Otherwise None is returned.
    """
    user = User.query.filter_by(username=username).first()
    return user


def get_user_email(username):
    """
    Retrieve user email if user exists.
    """
    user = get_user_by_username(username)

    if user:
        return user.email


def delete_user(username):
    """
    Delete user by username.

    If user does not exist return 0.
    """
    user = get_user_by_username(username)

    if user:
        db.session.delete(user)
        db.session.commit()
        return 1
    else:
        return 0


def get_ec2_group(name, user_id):
    """
    Retrieve EC2 group for user.

    If group does not exist raise exception.
    """
    group = EC2Group.query.filter_by(name=name, user_id=user_id).first()

    if not group:
        raise MashDBException(
            'Group {name} does not exist for EC2'.format(name=name)
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
    username,
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
        'requesting_user': username,
        'credentials': credentials
    }

    user = get_user_by_username(username)

    account = EC2Account(
        name=account_name,
        partition=partition,
        region=region_name,
        subnet=subnet,
        user_id=user.id
    )

    if group_name:
        group = _get_or_create_ec2_group(group_name, user.id)
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
            'credentials',
            'post',
            job_data=data
        )
        db.session.add(account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return account


def get_ec2_accounts(username):
    """
    Retrieve all EC2 accounts for user.
    """
    user = get_user_by_username(username)
    return user.ec2_accounts


def get_ec2_account(name, username):
    """
    Get EC2 account for given user.
    """
    ec2_account = EC2Account.query.filter(
        User.username == username
    ).filter_by(name=name).first()

    return ec2_account


def get_ec2_account_by_id(name, user_id):
    """
    Get EC2 account for given user.
    """
    try:
        ec2_account = EC2Account.query.filter_by(
            name=name, user_id=user_id
        ).one()
    except Exception:
        raise MashDBException(
            'EC2 account {name} does not exist for EC2'.format(name=name)
        )

    return ec2_account


def delete_ec2_account(name, username):
    """
    Delete EC2 account for user.
    """
    data = {
        'cloud': 'ec2',
        'account_name': name,
        'requesting_user': username
    }

    ec2_account = get_ec2_account(name, username)

    if ec2_account:
        try:
            db.session.delete(ec2_account)
            db.session.commit()
            handle_request(
                current_app.config['CREDENTIALS_URL'],
                'credentials',
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


def get_ec2_regions_by_partition(partition):
    """
    Get EC2 regions from config file based on partition.
    """
    regions = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['regions'][partition]
    )
    return regions


def get_ec2_helper_images():
    """
    Get helper image data for EC2 from config file.
    """
    helper_images = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['helper_images']
    )
    return helper_images


def add_target_ec2_account(
    account,
    accounts,
    cloud_accounts,
    helper_images,
    use_root_swap=None
):
    """
    Update job with account information.

    - Append any additional regions
    - Update ami for root swap if use_root_swap set
    """
    regions = get_ec2_regions_by_partition(account.partition)

    if account.additional_regions:
        for region in account.additional_regions:
            helper_images[region.name] = region.helper_image
            regions.append(region.name)

    job_doc_data = cloud_accounts.get(account.name, {})
    region = job_doc_data.get('region') or account.region
    subnet = job_doc_data.get('subnet') or account.subnet

    if use_root_swap:
        try:
            helper_image = job_doc_data['root_swap_ami']
        except KeyError:
            raise MashJobException(
                'root_swap_ami is required for account {0},'
                ' when using root swap.'.format(account)
            )
    else:
        helper_image = helper_images[region]

    accounts[region] = {
        'account': account.name,
        'target_regions': regions,
        'helper_image': helper_image,
        'subnet': subnet
    }


def convert_account_dict(accounts):
    """
    Create a dictionary of accounts by account name.
    """
    cloud_accounts = {}

    for account in accounts:
        cloud_accounts[account['name']] = account

    return cloud_accounts


def update_ec2_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.

    Once accounts dictionary is built remove cloud_groups
    and cloud_accounts keys from job_doc.
    """
    user = get_user_by_username(job_doc['requesting_user'])
    helper_images = get_ec2_helper_images()
    cloud_accounts = convert_account_dict(job_doc['cloud_accounts'])

    accounts = {}
    target_accounts = []
    for group_name in job_doc.get('cloud_groups', []):
        group = get_ec2_group(group_name, user.id)
        target_accounts += group.accounts

    for account_name in cloud_accounts:
        cloud_account = get_ec2_account_by_id(account_name, user.id)
        target_accounts.append(cloud_account)

    for account in target_accounts:
        if account.name not in accounts:
            add_target_ec2_account(
                account,
                accounts,
                cloud_accounts,
                helper_images,
                job_doc.get('use_root_swap')
            )

    if 'cloud_groups' in job_doc:
        del job_doc['cloud_groups']

    if 'cloud_accounts' in job_doc:
        del job_doc['cloud_accounts']

    job_doc['target_account_info'] = accounts

    return job_doc