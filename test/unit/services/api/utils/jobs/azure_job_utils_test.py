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

from pytest import raises
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.jobs.azure import validate_azure_job

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.jobs.azure.get_services_by_last_service')
@patch('mash.services.api.utils.jobs.azure.get_azure_account')
def test_update_azure_job_accounts(
    mock_get_azure_account, mock_get_services, mock_get_current_obj
):
    account = Mock()
    account.region = 'southcentralus'
    account.name = 'acnt1'
    mock_get_azure_account.return_value = account

    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'obs',
            'uploader',
            'create',
            'testing',
            'raw_image_uploader',
            'replication',
            'publisher',
            'deprecation'
        ]
    }
    mock_get_current_obj.return_value = app

    mock_get_services.return_value = [
        'obs',
        'uploader',
        'create',
        'testing',
        'raw_image_uploader',
        'replication',
        'publisher',
        'deprecation'
    ]

    job_doc = {
        'last_service': 'deprecation',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'source_resource_group': 'rg-1',
        'source_container': 'container1',
        'source_storage_account': 'sa1',
        'destination_resource_group': 'rg-2',
        'destination_container': 'container2',
        'destination_storage_account': 'sa2',
        'label': 'New Image 123',
        'offer_id': 'sles',
        'publisher_id': 'suse',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'old_cloud_image_name': 'Old test OEM Image'
    }

    # Missing args causes exception
    with raises(MashJobException):
        validate_azure_job(job_doc)

    job_doc['sku'] = '123'
    result = validate_azure_job(job_doc)

    assert result['region'] == 'southcentralus'
