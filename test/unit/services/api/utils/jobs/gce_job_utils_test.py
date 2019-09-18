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

from _pytest.python_api import raises

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.jobs.gce import update_gce_job_accounts, add_target_gce_account


@patch('mash.services.api.utils.jobs.gce.add_target_gce_account')
@patch('mash.services.api.utils.jobs.gce.get_gce_account_by_id')
@patch('mash.services.api.utils.jobs.gce.get_user_by_username')
def test_update_gce_job_accounts(
    mock_get_user,
    mock_get_gce_account,
    mock_add_target_account
):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    account = Mock()
    account.name = 'acnt1'
    mock_get_gce_account.return_value = account

    job_doc = {
        'requesting_user': 'user1',
        'cloud_account': 'acnt1'
    }

    result = update_gce_job_accounts(job_doc)

    assert 'target_account_info' in result
    assert 'cloud_accounts' not in result


def test_add_target_gce_account():
    account = Mock()
    account.region = 'us-east1'
    account.bucket = 'images'
    account.name = 'acnt1'
    account.testing_account = 'acnt2'
    account.is_publishing_account = True

    accounts = {}

    add_target_gce_account(
        account,
        accounts,
        None,
        None,
        None,
        family='sles'
    )

    assert 'us-east1' in accounts
    assert accounts['us-east1']['account'] == 'acnt1'
    assert accounts['us-east1']['bucket'] == 'images'
    assert accounts['us-east1']['testing_account'] == 'acnt2'
    assert accounts['us-east1']['is_publishing_account']

    # Missing family

    with raises(MashJobException):
        add_target_gce_account(
            account,
            accounts,
            None,
            None,
            None
        )

    # Publishing account has no testing account

    account.testing_account = None
    account.is_publishing_account = True

    with raises(MashJobException):
        add_target_gce_account(
            account,
            accounts,
            None,
            None,
            None,
            family='sles'
        )
