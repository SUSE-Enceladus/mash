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

from mash.services.api.utils.users import get_user_by_username
from mash.services.api.utils.accounts.azure import get_azure_account_by_id


def add_target_azure_account(
    account,
    accounts,
    region,
    source_container,
    source_resource_group,
    source_storage_account,
    destination_container,
    destination_resource_group,
    destination_storage_account
):
    """
    Update job with account information.
    """
    region = region or account.region
    source_container = source_container or account.source_container
    source_resource_group = \
        source_resource_group or account.source_resource_group
    source_storage_account = \
        source_storage_account or account.source_storage_account
    destination_container = destination_container or account.destination_container
    destination_resource_group = \
        destination_resource_group or account.destination_resource_group
    destination_storage_account = \
        destination_storage_account or account.destination_storage_account

    accounts[region] = {
        'account': account.name,
        'source_container': source_container,
        'source_resource_group': source_resource_group,
        'source_storage_account': source_storage_account,
        'destination_container': destination_container,
        'destination_resource_group': destination_resource_group,
        'destination_storage_account': destination_storage_account
    }


def update_azure_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.
    """
    user = get_user_by_username(job_doc['requesting_user'])
    cloud_account = get_azure_account_by_id(job_doc['cloud_account'], user.id)
    accounts = {}

    add_target_azure_account(
        cloud_account,
        accounts,
        job_doc.get('region'),
        job_doc.get('source_container'),
        job_doc.get('source_resource_group'),
        job_doc.get('source_storage_account'),
        job_doc.get('destination_container'),
        job_doc.get('destination_resource_group'),
        job_doc.get('destination_storage_account')
    )

    job_doc['target_account_info'] = accounts

    return job_doc
