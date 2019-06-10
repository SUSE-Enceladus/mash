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

gce_account = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'bucket': non_empty_string,
        'group': non_empty_string,
        'cloud': {'enum': ['gce']},
        'testing_account': non_empty_string,
        'region': non_empty_string,
        'requesting_user': non_empty_string,
        'is_publishing_account': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'bucket',
        'cloud',
        'requesting_user',
        'region'
    ]
}

gce_credentials = {
    'type': 'object',
    'properties': {
        'type': non_empty_string,
        'project_id': non_empty_string,
        'private_key_id': non_empty_string,
        'private_key': non_empty_string,
        'client_email': non_empty_string,
        'client_id': non_empty_string,
        'auth_uri': non_empty_string,
        'token_uri': non_empty_string,
        'auth_provider_x509_cert_url': non_empty_string,
        'client_x509_cert_url': non_empty_string
    },
    'additionalProperties': False,
    'required': [
        'type',
        'project_id',
        'private_key_id',
        'private_key',
        'client_email',
        'client_id',
        'auth_uri',
        'token_uri',
        'auth_provider_x509_cert_url',
        'client_x509_cert_url'
    ]
}

add_account_gce = copy.deepcopy(gce_account)
add_account_gce['properties']['credentials'] = gce_credentials
add_account_gce['required'].append('credentials')
