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

azure_job_account = {
    'type': 'object',
    'properties': {
        'name': non_empty_string,
        'region': non_empty_string,
        'source_container': non_empty_string,
        'source_resource_group': non_empty_string,
        'source_storage_account': non_empty_string,
        'destination_container': non_empty_string,
        'destination_resource_group': non_empty_string,
        'destination_storage_account': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}

azure_job_message = copy.deepcopy(base_job_message)
azure_job_message['properties']['cloud'] = {'enum': ['azure']}
azure_job_message['properties']['emails'] = non_empty_string
azure_job_message['properties']['label'] = non_empty_string
azure_job_message['properties']['offer_id'] = non_empty_string
azure_job_message['properties']['publisher_id'] = non_empty_string
azure_job_message['properties']['sku'] = non_empty_string
azure_job_message['properties']['vm_images_key'] = non_empty_string
azure_job_message['properties']['publish_offer'] = {'type': 'boolean'}
azure_job_message['required'].append('emails')
azure_job_message['required'].append('label')
azure_job_message['required'].append('offer_id')
azure_job_message['required'].append('publisher_id')
azure_job_message['required'].append('sku')
azure_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': azure_job_account,
    'minItems': 1
}
