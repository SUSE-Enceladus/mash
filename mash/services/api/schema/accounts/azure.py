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

import copy

from mash.services.api.schema import string_with_example

azure_account = {
    'type': 'object',
    'properties': {
        'account_name': string_with_example('account1'),
        'region': string_with_example('westus'),
        'requesting_user': string_with_example('user1'),
        'source_container': string_with_example('container1'),
        'source_resource_group': string_with_example('res_group1'),
        'source_storage_account': string_with_example('storage_account1'),
        'destination_container': string_with_example('container2'),
        'destination_resource_group': string_with_example('res_group2'),
        'destination_storage_account': string_with_example('storage_account2')
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'region',
        'requesting_user',
        'source_container',
        'source_resource_group',
        'source_storage_account',
        'destination_container',
        'destination_resource_group',
        'destination_storage_account'
    ]
}

azure_credentials = {
    'type': 'object',
    'properties': {
        'clientId': string_with_example(
            '0f12f123-1234-4321-1234-f123456f1234'
        ),
        'clientSecret': string_with_example(
            '0f12f123-1234-4321-1234-f123456f1234'
        ),
        'subscriptionId': string_with_example(
            '0f12f123-1234-4321-1234-f123456f1234'
        ),
        'tenantId': string_with_example(
            '0f12f123-1234-4321-1234-f123456f1234'
        ),
        'activeDirectoryEndpointUrl': string_with_example(
            'https://login.microsoftonline.com'
        ),
        'resourceManagerEndpointUrl': string_with_example(
            'https://management.azure.com/'
        ),
        'activeDirectoryGraphResourceId': string_with_example(
            'https://graph.windows.net/'
        ),
        'sqlManagementEndpointUrl': string_with_example(
            'https://management.core.windows.net:8443/'
        ),
        'galleryEndpointUrl': string_with_example(
            'https://gallery.azure.com/'
        ),
        'managementEndpointUrl': string_with_example(
            'https://management.core.windows.net/'
        )
    },
    'additionalProperties': False,
    'required': [
        'clientId',
        'clientSecret',
        'subscriptionId',
        'tenantId',
        'activeDirectoryEndpointUrl',
        'resourceManagerEndpointUrl',
        'activeDirectoryGraphResourceId',
        'sqlManagementEndpointUrl',
        'galleryEndpointUrl',
        'managementEndpointUrl'
    ],
}

add_account_azure = copy.deepcopy(azure_account)
add_account_azure['properties']['credentials'] = azure_credentials
add_account_azure['required'].append('credentials')
