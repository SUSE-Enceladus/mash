# Copyright (c) 2024 SUSE LLC.  All rights reserved.
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
from mash.services.api.v1.utils.jobs.azure import validate_azure_job

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.v1.utils.jobs.azure.get_services_by_last_service')
@patch('mash.services.api.v1.utils.jobs.azure.get_azure_account')
def test_update_azure_job_accounts(
    mock_get_azure_account, mock_get_services, mock_get_current_obj
):
    account = {
        'name': 'acnt1',
        'region': 'westus',
        'source_container': 'container',
        'source_resource_group': 'rg1',
        'source_storage_account': 'sa1'
    }
    mock_get_azure_account.return_value = account

    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'download',
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
        'download',
        'upload',
        'create',
        'test',
        'raw_image_upload',
        'replicate',
        'publish'
    ]

    job_doc = {
        'last_service': 'publish',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'sku': 'gen1',
        'generation_id': 'gen2',
        'offer_id': 'offer1',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    result = validate_azure_job(job_doc)

    assert result['region'] == 'westus'

    # Matching sku & generation id
    job_doc['generation_id'] = 'gen1'

    with raises(MashJobException):
        validate_azure_job(job_doc)

    # Missing offer_id
    del job_doc['offer_id']

    with raises(MashJobException):
        validate_azure_job(job_doc)
