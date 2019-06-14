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

from mash.services.api.schema import non_empty_string

additional_regions = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': non_empty_string,
            'helper_image': non_empty_string
        },
        'required': ['name', 'helper_image'],
        'additionalProperties': False
    },
    'minItems': 1
}

ec2_account = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'additional_regions': additional_regions,
        'group': non_empty_string,
        'partition': non_empty_string,
        'region': non_empty_string,
        'requesting_user': non_empty_string,
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'requesting_user',
        'region'
    ]
}

ec2_credentials = {
    'type': 'object',
    'properties': {
        'access_key_id': non_empty_string,
        'secret_access_key': non_empty_string
    },
    'additionalProperties': False,
    'required': ['access_key_id', 'secret_access_key']
}

add_account_ec2 = copy.deepcopy(ec2_account)
add_account_ec2['properties']['credentials'] = ec2_credentials
add_account_ec2['required'].append('credentials')
