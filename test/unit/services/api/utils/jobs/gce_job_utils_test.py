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

from pytest import raises

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.jobs.gce import update_gce_job_accounts


@patch('mash.services.api.utils.jobs.gce.get_gce_account')
def test_update_gce_job_accounts(
    mock_get_gce_account
):
    account = Mock()
    account.name = 'acnt1'
    account.region = 'us-east1'
    account.bucket = 'images'
    account.testing_account = 'acnt2'
    account.is_publishing_account = True
    mock_get_gce_account.return_value = account

    job_doc = {
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'bucket': 'images2',
        'family': 'sles'
    }

    result = update_gce_job_accounts(job_doc)

    assert result['region'] == 'us-east1'
    assert result['bucket'] == 'images2'
    assert result['testing_account'] == 'acnt2'

    # Missing family
    del job_doc['family']

    with raises(MashJobException):
        update_gce_job_accounts(job_doc)

    # Publishing account has no testing account
    del job_doc['testing_account']
    job_doc['family'] = 'sles'
    account.testing_account = None

    with raises(MashJobException):
        update_gce_job_accounts(job_doc)
