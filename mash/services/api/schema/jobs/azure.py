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

azure_job_message = copy.deepcopy(base_job_message)
azure_job_message['properties']['emails'] = string_with_example(
    'test@fake.com'
)
azure_job_message['properties']['label'] = string_with_example(
    'openSUSE Leap 15'
)
azure_job_message['properties']['offer_id'] = string_with_example('leap')
azure_job_message['properties']['publisher_id'] = string_with_example('suse')
azure_job_message['properties']['sku'] = string_with_example('15')
azure_job_message['properties']['vm_images_key'] = string_with_example(
    'microsoft-azure-corevm.vmImagesPublicAzure'
)
azure_job_message['properties']['publish_offer'] = {'type': 'boolean'}
azure_job_message['properties']['cloud_account'] = string_with_example(
    'account1'
)
azure_job_message['properties']['source_container'] = string_with_example(
    'container1'
)
azure_job_message['properties']['source_resource_group'] = string_with_example(
    'res_group1'
)
azure_job_message['properties']['source_storage_account'] = string_with_example(
    'storage_account1'
)
azure_job_message['properties']['destination_container'] = string_with_example(
    'container2'
)
azure_job_message['properties']['destination_resource_group'] = string_with_example(
    'res_group2'
)
azure_job_message['properties']['destination_storage_account'] = string_with_example(
    'storage_account2'
)
azure_job_message['properties']['region'] = string_with_example('westus')

azure_job_message['required'].append('emails')
azure_job_message['required'].append('label')
azure_job_message['required'].append('offer_id')
azure_job_message['required'].append('publisher_id')
azure_job_message['required'].append('sku')
azure_job_message['required'].append('cloud_account')
azure_job_message['properties']['image']['example'] = \
    'openSUSE-Leap-15.0-Azure'
azure_job_message['properties']['cloud_image_name']['example'] = \
    'opensuse-leap-15-v{date}'
azure_job_message['properties']['old_cloud_image_name']['example'] = \
    'opensuse-leap-15-v20190520'
azure_job_message['properties']['image_description']['example'] = \
    'openSUSE Leap 15'
azure_job_message['properties']['instance_type']['example'] = 'Standard_B1ms'
