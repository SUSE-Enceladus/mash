# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

aliyun_account = {
    'type': 'object',
    'properties': {
        'account_name': string_with_example('account1'),
        'bucket': string_with_example('image-bucket'),
        'region': string_with_example('cn-beijing'),
        'security_group_id': string_with_example('sg1'),
        'vswitch_id': string_with_example('vs1')
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'bucket',
        'region'
    ]
}

aliyun_credentials = {
    'type': 'object',
    'properties': {
        'access_key': string_with_example(
            '123456789'
        ),
        'access_secret': string_with_example(
            '987654321'
        )
    },
    'additionalProperties': False,
    'required': [
        'access_key',
        'access_secret'
    ]
}

add_account_aliyun = copy.deepcopy(aliyun_account)
add_account_aliyun['properties']['credentials'] = aliyun_credentials
add_account_aliyun['required'].append('credentials')

aliyun_account_update = {
    'type': 'object',
    'properties': {
        'bucket': string_with_example('image-bucket'),
        'region': string_with_example('cn-beijing'),
        'security_group_id': string_with_example('sg1'),
        'vswitch_id': string_with_example('vs1'),
        'credentials': aliyun_credentials
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['bucket']},
        {'required': ['region']},
        {'required': ['security_group_id']},
        {'required': ['vswitch_id']},
        {'required': ['credentials']}
    ]
}
