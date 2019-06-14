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
from mash.services.api.schema.jobs import base_job_message

account_numbers = {
    'type': 'string',
    'format': 'regex',
    'pattern': '^[0-9]{12}(,[0-9]{12})*$'
}

ec2_job_account = {
    'type': 'object',
    'properties': {
        'name': non_empty_string,
        'region': non_empty_string,
        'root_swap_ami': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}

ec2_job_message = copy.deepcopy(base_job_message)
ec2_job_message['properties']['share_with'] = {
    'anyOf': [
        {'enum': ['all', 'none']},
        account_numbers
    ]
}
ec2_job_message['properties']['allow_copy'] = {'type': 'boolean'}
ec2_job_message['properties']['billing_codes'] = non_empty_string
ec2_job_message['properties']['use_root_swap'] = {'type': 'boolean'}
ec2_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': ec2_job_account,
    'minItems': 1
}
