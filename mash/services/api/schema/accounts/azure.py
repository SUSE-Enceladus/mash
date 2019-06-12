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

from mash.services.api.schema.base import non_empty_string

azure_account = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'group': non_empty_string,
        'region': non_empty_string,
        'requesting_user': non_empty_string,
        'source_container': non_empty_string,
        'source_resource_group': non_empty_string,
        'source_storage_account': non_empty_string,
        'destination_container': non_empty_string,
        'destination_resource_group': non_empty_string,
        'destination_storage_account': non_empty_string
    },
    'additionalProperties': False,
    'required': [
        'account_name',
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
        'clientId': non_empty_string,
        'clientSecret': non_empty_string,
        'subscriptionId': non_empty_string,
        'tenantId': non_empty_string,
        'activeDirectoryEndpointUrl': non_empty_string,
        'resourceManagerEndpointUrl': non_empty_string,
        'activeDirectoryGraphResourceId': non_empty_string,
        'sqlManagementEndpointUrl': non_empty_string,
        'galleryEndpointUrl': non_empty_string,
        'managementEndpointUrl': non_empty_string
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
