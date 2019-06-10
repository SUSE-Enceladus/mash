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
from mash.services.api.schema.jobs import base_job_message

share_with = {
    'type': 'string',
    'format': 'regex',
    'pattern': '^[0-9]{12}(,[0-9]{12})*$|^(all|none)$',
    'example': '123456789012,098765432109',
    'examples': ['all', 'none', '123456789012,098765432109']
}

ec2_job_account = {
    'type': 'object',
    'properties': {
        'name': string_with_example('account1'),
        'region': string_with_example('us-east-1'),
        'root_swap_ami': string_with_example('ami-1234567890'),
        'subnet': string_with_example('subnet-12345678')
    },
    'additionalProperties': False,
    'required': ['name']
}

ec2_job_message = copy.deepcopy(base_job_message)
ec2_job_message['properties']['share_with'] = share_with
ec2_job_message['properties']['allow_copy'] = {'type': 'boolean'}
ec2_job_message['properties']['billing_codes'] = string_with_example(
    'bp-1234567890,bp-0987654321'
)
ec2_job_message['properties']['use_root_swap'] = {'type': 'boolean'}
ec2_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': ec2_job_account,
    'minItems': 1,
    'example': [{'name': 'account1'}]
}
