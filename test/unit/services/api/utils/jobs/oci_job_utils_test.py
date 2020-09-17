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
from mash.services.api.utils.jobs.oci import validate_oci_job

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.jobs.oci.get_services_by_last_service')
@patch('mash.services.api.utils.jobs.oci.get_oci_account')
def test_validate_oci_job(
    mock_get_oci_account, mock_get_services, mock_get_current_obj
):
    account = {
        'name': 'acnt1',
        'region': 'us-phoenix-1',
        'bucket': 'images',
        'availability_domain': 'Omic:PHX-AD-1',
        'compartment_id': 'ocid1.compartment.oc1..',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..'
    }
    mock_get_oci_account.return_value = account

    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'obs',
            'upload',
            'create',
            'test',
            'raw_image_upload',
            'replicate',
            'publish',
            'deprecate'
        ]
    }
    mock_get_current_obj.return_value = app

    mock_get_services.return_value = [
        'obs',
        'upload',
        'create',
        'test'
    ]

    job_doc = {
        'last_service': 'test',
        'requesting_user': 1,
        'cloud_account': 'acnt1',
        'bucket': 'images2',
        'operating_system': 'sles',
        'operating_system_version': '14',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    result = validate_oci_job(job_doc)

    assert result['region'] == 'us-phoenix-1'
    assert result['bucket'] == 'images2'
    assert result['availability_domain'] == 'Omic:PHX-AD-1'
    assert result['compartment_id'] == 'ocid1.compartment.oc1..'
    assert result['oci_user_id'] == 'ocid1.user.oc1..'
    assert result['tenancy'] == 'ocid1.tenancy.oc1..'

    del job_doc['operating_system']
    with raises(MashJobException):
        validate_oci_job(job_doc)
