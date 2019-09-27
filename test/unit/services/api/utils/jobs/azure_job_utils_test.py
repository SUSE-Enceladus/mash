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

from unittest.mock import patch, Mock

from mash.services.api.utils.jobs.azure import (
    update_azure_job_accounts,
    add_target_azure_account
)


@patch('mash.services.api.utils.jobs.azure.add_target_azure_account')
@patch('mash.services.api.utils.jobs.azure.get_azure_account_by_id')
@patch('mash.services.api.utils.jobs.azure.get_user_by_username')
def test_update_azure_job_accounts(
    mock_get_user,
    mock_get_azure_account,
    mock_add_target_account
):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    account = Mock()
    account.name = 'acnt1'
    mock_get_azure_account.return_value = account

    job_doc = {
        'requesting_user': 'user1',
        'cloud_account': 'acnt1',
        'region': 'southcentralus',
        'source_resource_group': 'rg-1',
        'source_container': 'container1',
        'source_storage_account': 'sa1',
        'destination_resource_group': 'rg-2',
        'destination_container': 'container2',
        'destination_storage_account': 'sa2'
    }

    result = update_azure_job_accounts(job_doc)

    assert 'target_account_info' in result


def test_add_target_azure_account():
    account = Mock()
    account.region = 'useast'
    account.name = 'acnt1'
    account.source_container = 'container1'
    account.source_resource_group = 'group1'
    account.source_storage_account = 'account1'
    account.destination_container = 'container2'
    account.destination_resource_group = 'group2'
    account.destination_storage_account = 'account2'

    accounts = {}

    add_target_azure_account(
        account,
        accounts,
        None,
        None,
        None,
        None,
        None,
        None,
        None
    )

    assert 'useast' in accounts
    assert accounts['useast']['account'] == 'acnt1'
    assert accounts['useast']['source_container'] == 'container1'
    assert accounts['useast']['source_resource_group'] == 'group1'
    assert accounts['useast']['source_storage_account'] == 'account1'
    assert accounts['useast']['destination_container'] == 'container2'
    assert accounts['useast']['destination_resource_group'] == 'group2'
    assert accounts['useast']['destination_storage_account'] == 'account2'
