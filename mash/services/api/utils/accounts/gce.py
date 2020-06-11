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
from mash.services.api.models import GCEAccount
from mash.utils.mash_utils import handle_request


def create_gce_account(
    user_id,
    account_name,
    bucket,
    region_name,
    credentials,
    test_account,
    is_publishing_account
):
    """
    Create a new GCE account for user.
    """
    if is_publishing_account and not test_account:
        raise MashDBException(
            'Jobs using a GCE publishing account require'
            ' the use of a test account.'
        )

    data = {
        'cloud': 'gce',
        'account_name': account_name,
        'requesting_user': user_id,
        'credentials': credentials
    }

    account = GCEAccount(
        name=account_name,
        bucket=bucket,
        region=region_name,
        test_account=test_account,
        is_publishing_account=is_publishing_account,
        user_id=user_id
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


def get_gce_accounts(user_id):
    """
    Retrieve all GCE accounts for user.
    """
    user = get_user_by_id(user_id)
    return user.gce_accounts


def get_gce_account(name, user_id):
    """
    Get GCE account for given user.
    """
    try:
        gce_account = GCEAccount.query.filter_by(
            name=name, user_id=user_id
        ).one()
    except Exception:
        raise MashDBException(
            'GCE account {name} does not exist'.format(name=name)
        )

    return gce_account


def delete_gce_account(name, user_id):
    """
    Delete GCE account for user.
    """
    data = {
        'cloud': 'gce',
        'account_name': name,
        'requesting_user': user_id
    }

    gce_account = get_gce_account(name, user_id)

    if gce_account:
        try:
            db.session.delete(gce_account)
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


def update_gce_account(
    account_name,
    user_id,
    bucket=None,
    region=None,
    credentials=None,
    test_account=None
):
    """
    Update an existing GCE account.
    """
    gce_account = get_gce_account(account_name, user_id)

    if not gce_account:
        return None

    if credentials:
        data = {
            'cloud': 'gce',
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

    if bucket:
        gce_account.bucket = bucket

    if region:
        gce_account.region = region

    if test_account and gce_account.is_publishing_account:
        gce_account.test_account = test_account

    try:
        db.session.add(gce_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return gce_account
