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

from unittest.mock import patch, Mock

from mash.services.api.utils.jobs.oci import update_oci_job_accounts


@patch('mash.services.api.utils.jobs.oci.get_oci_account_by_id')
@patch('mash.services.api.utils.jobs.oci.get_user_by_username')
def test_update_oci_job_accounts(
    mock_get_user,
    mock_get_oci_account
):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    account = Mock()
    account.name = 'acnt1'
    account.region = 'us-phoenix-1'
    account.bucket = 'images'
    account.availability_domain = 'Omic:PHX-AD-1'
    account.compartment_id = 'ocid1.compartment.oc1..'
    account.oci_user_id = 'ocid1.user.oc1..'
    account.tenancy = 'ocid1.tenancy.oc1..'
    mock_get_oci_account.return_value = account

    job_doc = {
        'requesting_user': 'user1',
        'cloud_account': 'acnt1',
        'bucket': 'images2'
    }

    result = update_oci_job_accounts(job_doc)

    assert result['region'] == 'us-phoenix-1'
    assert result['bucket'] == 'images2'
    assert result['availability_domain'] == 'Omic:PHX-AD-1'
    assert result['compartment_id'] == 'ocid1.compartment.oc1..'
    assert result['oci_user_id'] == 'ocid1.user.oc1..'
    assert result['tenancy'] == 'ocid1.tenancy.oc1..'
