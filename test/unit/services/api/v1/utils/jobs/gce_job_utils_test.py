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
from mash.services.api.v1.utils.jobs.gce import validate_gce_job

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.v1.utils.jobs.gce.get_services_by_last_service')
@patch('mash.services.api.v1.utils.jobs.gce.get_gce_account')
def test_update_gce_job_accounts(
    mock_get_gce_account, mock_get_services, mock_get_current_obj
):
    account = {
        'name': 'acnt1',
        'region': 'us-east1',
        'bucket': 'images',
        'testing_account': 'acnt2',
        'is_publishing_account': True
    }
    mock_get_gce_account.return_value = account

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
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'bucket': 'images2',
        'family': 'sles',
        'image_project': 'suse-cloud',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    result = validate_gce_job(job_doc)

    assert result['region'] == 'us-east1'
    assert result['bucket'] == 'images2'
    assert result['testing_account'] == 'acnt2'

    # Missing family
    del job_doc['family']

    with raises(MashJobException):
        validate_gce_job(job_doc)

    # Publishing account has no test account
    del job_doc['testing_account']
    job_doc['family'] = 'sles'
    account['testing_account'] = None

    with raises(MashJobException):
        validate_gce_job(job_doc)

    # Publishing account has no image_project
    del job_doc['image_project']
    job_doc['testing_account'] = 'acnt2'

    with raises(MashJobException):
        validate_gce_job(job_doc)
