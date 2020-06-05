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

from pytest import raises

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.jobs.oci import update_oci_job_accounts


@patch('mash.services.api.utils.jobs.oci.get_services_by_last_service')
@patch('mash.services.api.utils.jobs.oci.get_oci_account')
def test_update_oci_job_accounts(
    mock_get_oci_account, mock_get_services
):
    account = Mock()
    account.name = 'acnt1'
    account.region = 'us-phoenix-1'
    account.bucket = 'images'
    account.availability_domain = 'Omic:PHX-AD-1'
    account.compartment_id = 'ocid1.compartment.oc1..'
    account.oci_user_id = 'ocid1.user.oc1..'
    account.tenancy = 'ocid1.tenancy.oc1..'
    mock_get_oci_account.return_value = account

    mock_get_services.return_value = [
        'obs',
        'uploader',
        'create',
        'testing'
    ]

    job_doc = {
        'last_service': 'testing',
        'requesting_user': 1,
        'cloud_account': 'acnt1',
        'bucket': 'images2',
        'operating_system': 'sles',
        'operating_system_version': '14'
    }

    result = update_oci_job_accounts(job_doc)

    assert result['region'] == 'us-phoenix-1'
    assert result['bucket'] == 'images2'
    assert result['availability_domain'] == 'Omic:PHX-AD-1'
    assert result['compartment_id'] == 'ocid1.compartment.oc1..'
    assert result['oci_user_id'] == 'ocid1.user.oc1..'
    assert result['tenancy'] == 'ocid1.tenancy.oc1..'

    del job_doc['operating_system']
    with raises(MashJobException):
        update_oci_job_accounts(job_doc)
