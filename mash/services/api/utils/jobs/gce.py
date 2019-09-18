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

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.users import get_user_by_username
from mash.services.api.utils.accounts.gce import get_gce_account_by_id


def add_target_gce_account(
    account,
    accounts,
    bucket=None,
    region=None,
    testing_account=None,
    family=None
):
    """
    Update job with account information.
    """
    testing_account = testing_account or account.testing_account
    region = region or account.region
    bucket = bucket or account.bucket

    if account.is_publishing_account and not family:
        raise MashJobException(
            'Jobs using a GCE publishing account require a family.'
        )

    if account.is_publishing_account and not testing_account:
        raise MashJobException(
            'Jobs using a GCE publishing account require'
            ' the use of a testing account.'
        )

    accounts[region] = {
        'account': account.name,
        'bucket': bucket,
        'is_publishing_account': account.is_publishing_account
    }

    if testing_account:
        accounts[region]['testing_account'] = testing_account


def update_gce_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.
    """
    user = get_user_by_username(job_doc['requesting_user'])
    cloud_account = get_gce_account_by_id(job_doc['cloud_account'], user.id)
    accounts = {}

    add_target_gce_account(
        cloud_account,
        accounts,
        job_doc.get('bucket'),
        job_doc.get('region'),
        job_doc.get('testing_account'),
        job_doc.get('family')
    )

    job_doc['target_account_info'] = accounts

    return job_doc
