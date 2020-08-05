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

from mash.mash_exceptions import MashDBException
from mash.services.database.extensions import db
from mash.services.api.utils.users import get_user_by_id
from mash.services.database.models import OCIAccount
from mash.utils.mash_utils import handle_request, get_fingerprint_from_private_key


def create_oci_account(
    user_id,
    account_name,
    bucket,
    region_name,
    availability_domain,
    compartment_id,
    oci_user_id,
    tenancy,
    signing_key
):
    """
    Create a new OCI account for user.
    """
    data = {
        'cloud': 'oci',
        'account_name': account_name,
        'requesting_user': user_id,
        'credentials': {
            'signing_key': signing_key,
            'fingerprint': get_fingerprint_from_private_key(signing_key)
        }
    }

    account = OCIAccount(
        name=account_name,
        bucket=bucket,
        region=region_name,
        availability_domain=availability_domain,
        compartment_id=compartment_id,
        oci_user_id=oci_user_id,
        tenancy=tenancy,
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


def get_oci_accounts(user_id):
    """
    Retrieve all OCI accounts for user.
    """
    user = get_user_by_id(user_id)
    return user.oci_accounts


def get_oci_account(name, user_id):
    """
    Get OCI account for given user.
    """
    try:
        oci_account = OCIAccount.query.filter_by(
            name=name, user_id=user_id
        ).one()
    except Exception:
        raise MashDBException(
            'OCI account {name} does not exist'.format(name=name)
        )

    return oci_account


def delete_oci_account(name, user_id):
    """
    Delete OCI account for user.
    """
    data = {
        'cloud': 'oci',
        'account_name': name,
        'requesting_user': user_id
    }

    oci_account = get_oci_account(name, user_id)

    if oci_account:
        try:
            db.session.delete(oci_account)
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


def update_oci_account(
    user_id,
    account_name,
    bucket=None,
    region=None,
    availability_domain=None,
    compartment_id=None,
    oci_user_id=None,
    tenancy=None,
    signing_key=None
):
    """
    Update an existing OCI account.
    """
    oci_account = get_oci_account(account_name, user_id)

    if not oci_account:
        return None

    if signing_key:
        data = {
            'cloud': 'oci',
            'account_name': account_name,
            'requesting_user': user_id,
            'credentials': {
                'signing_key': signing_key,
                'fingerprint': get_fingerprint_from_private_key(signing_key)
            }
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
        oci_account.bucket = bucket

    if region:
        oci_account.region = region

    if availability_domain:
        oci_account.availability_domain = availability_domain

    if compartment_id:
        oci_account.compartment_id = compartment_id

    if oci_user_id:
        oci_account.oci_user_id = oci_user_id

    if tenancy:
        oci_account.tenancy = tenancy

    try:
        db.session.add(oci_account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return oci_account
