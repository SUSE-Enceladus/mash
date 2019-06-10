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

gce_job_account = {
    'type': 'object',
    'properties': {
        'bucket': string_with_example('image-bucket'),
        'name': string_with_example('account1'),
        'region': string_with_example('us-west1-a')
    },
    'additionalProperties': False,
    'required': ['name']
}

gce_job_message = copy.deepcopy(base_job_message)
gce_job_message['properties']['cloud'] = {'enum': ['gce']}
gce_job_message['properties']['family'] = string_with_example('opensuse-leap')
gce_job_message['properties']['months_to_deletion'] = {
    'type': 'integer',
    'minimum': 0,
    'example': 6
}
gce_job_message['properties']['guest_os_features'] = {
    'type': 'array',
    'items': string_with_example('UEFI_COMPATIBLE'),
    'uniqueItems': True,
    'minItems': 1
}
gce_job_message['properties']['test_fallback_regions'] = {
    'type': 'array',
    'items': string_with_example('us-west1-a'),
    'minItems': 0
}
gce_job_message['properties']['testing_account'] = string_with_example(
    'testaccount1'
)
gce_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': gce_job_account,
    'minItems': 1,
    'example': [{'name': 'account1'}]
}
gce_job_message['properties']['image']['example'] = 'openSUSE-Leap-15.0-GCE'
gce_job_message['properties']['cloud_image_name']['example'] = \
    'opensuse-leap-15-v{date}'
gce_job_message['properties']['old_cloud_image_name']['example'] = \
    'opensuse-leap-15-v20190520'
gce_job_message['properties']['image_description']['example'] = \
    'openSUSE Leap 15'
gce_job_message['properties']['instance_type']['example'] = 'n1-standard-1'
