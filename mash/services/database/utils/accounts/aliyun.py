# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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
from mash.services.database.models import AliyunAccount
from mash.utils.mash_utils import handle_request


def create_new_aliyun_account(
    user_id,
    account_name,
    bucket_name,
    region_name,
    credentials,
    security_group_id=None,
    vswitch_id=None
):
    """
    Create a new Aliyun account for user.
    """
    data = {
        'cloud': 'aliyun',
        'account_name': account_name,
        'requesting_user': user_id,
        'credentials': credentials
    }

    aliyun_account = AliyunAccount(
        name=account_name,
        region=region_name,
        bucket=bucket_name,
        security_group_id=security_group_id,
        vswitch_id=vswitch_id,
        user_id=user_id
    )

    if security_group_id:
        aliyun_account.security_group_id = security_group_id

    if vswitch_id:
        aliyun_account.vswitch_id = vswitch_id

    try:
        handle_request(
            current_app.config['CREDENTIALS_URL'],
            'credentials/',
            'post',
            job_data=data
        )
        db.session.add(aliyun_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return aliyun_account


def get_aliyun_accounts(user_id):
    """
    Retrieve all Aliyun accounts for user.
    """
    user = get_user_by_id(user_id)
    return user.aliyun_accounts


def get_aliyun_account_for_user(name, user_id):
    """
    Get Aliyun account for given user.
    """
    try:
        aliyun_account = AliyunAccount.query.filter_by(
            name=name,
            user_id=user_id
        ).one()
    except NoResultFound:
        aliyun_account = None

    return aliyun_account


def delete_aliyun_account_for_user(name, user_id):
    """
    Delete Aliyun account for user.
    """
    data = {
        'cloud': 'aliyun',
        'account_name': name,
        'requesting_user': user_id
    }

    aliyun_account = get_aliyun_account_for_user(name, user_id)

    if aliyun_account:
        try:
            db.session.delete(aliyun_account)
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


def update_aliyun_account_for_user(
    account_name,
    user_id,
    bucket=None,
    region=None,
    credentials=None,
    security_group_id=None,
    vswitch_id=None
):
    """
    Update an existing Aliyun account.
    """
    aliyun_account = get_aliyun_account_for_user(account_name, user_id)

    if not aliyun_account:
        return None

    if credentials:
        data = {
            'cloud': 'aliyun',
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

    if region:
        aliyun_account.region = region

    if bucket:
        aliyun_account.bucket = bucket

    if security_group_id:
        aliyun_account.security_group_id = security_group_id

    if vswitch_id:
        aliyun_account.vswitch_id = vswitch_id

    try:
        db.session.add(aliyun_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return aliyun_account
