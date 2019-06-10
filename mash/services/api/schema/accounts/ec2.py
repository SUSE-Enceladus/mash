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

additional_regions = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': string_with_example('us-east-44'),
            'helper_image': string_with_example('ami-1234567890')
        },
        'required': ['name', 'helper_image'],
        'additionalProperties': False
    },
    'minItems': 1,
    'example': [{'name': 'us-east-44', 'helper_image': 'ami-1234567890'}]
}

partition = {
    'type': 'string',
    'enum': ['aws', 'aws-cn', 'aws-us-gov']
}

ec2_account = {
    'type': 'object',
    'properties': {
        'account_name': string_with_example('account1'),
        'additional_regions': additional_regions,
        'group': string_with_example('group1'),
        'partition': partition,
        'region': string_with_example('us-east-1'),
        'subnet': string_with_example('subnet-12345678'),
        'requesting_user': string_with_example('user1'),
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
        'access_key_id': string_with_example('AKIAIOSFODNN7EXAMPLE'),
        'secret_access_key': string_with_example(
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )
    },
    'additionalProperties': False,
    'required': ['access_key_id', 'secret_access_key']
}

add_account_ec2 = copy.deepcopy(ec2_account)
add_account_ec2['properties']['credentials'] = ec2_credentials
add_account_ec2['required'].append('credentials')
