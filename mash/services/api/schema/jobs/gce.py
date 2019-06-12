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
from mash.services.api.schema.jobs.base import base_job_message

gce_job_account = {
    'type': 'object',
    'properties': {
        'bucket': non_empty_string,
        'name': non_empty_string,
        'region': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}

gce_job_message = copy.deepcopy(base_job_message)
gce_job_message['properties']['family'] = non_empty_string
gce_job_message['properties']['months_to_deletion'] = {
    'type': 'integer',
    'minimum': 0
}
gce_job_message['properties']['testing_account'] = non_empty_string
gce_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': gce_job_account,
    'minItems': 1
}
