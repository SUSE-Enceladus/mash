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
    'test@fake.com',
    description='A Comma-separated list of email addresses to be notified '
                'of the progress of the publishing operation.'
)
azure_job_message['properties']['label'] = string_with_example(
    'openSUSE Leap 15',
    description='The title to be displayed in the marketplace.'
)
azure_job_message['properties']['offer_id'] = string_with_example(
    'leap',
    description='The name of a group of related images created by a '
                'publisher.'
)
azure_job_message['properties']['publisher_id'] = string_with_example(
    'suse',
    description='The organization that created the image'
)
azure_job_message['properties']['sku'] = string_with_example(
    '15',
    description='The instance of an offer, such as a major release of '
                'a distribution.'
)
azure_job_message['properties']['generation_id'] = string_with_example(
    'gen2',
    description='The key to use for a second generation if supporting '
                'multiple disk generations.'
)
azure_job_message['properties']['cloud_image_name_generation_suffix'] = string_with_example(
    'gen2',
    description='The suffix is appended to the cloud image name '
)
azure_job_message['properties']['vm_images_key'] = string_with_example(
    'microsoft-azure-corevm.vmImagesPublicAzure',
    description='Dictionary key where sku information is found in the '
                'offer doc.'
)
azure_job_message['properties']['publish_offer'] = {
    'type': 'boolean',
    'description': 'Whether to start the image publish process.'
}
azure_job_message['properties']['cloud_account'] = string_with_example(
    'account1',
    description='The name of the cloud account credentials to use for image '
                'publishing.'
)
azure_job_message['properties']['source_container'] = string_with_example(
    'container1',
    description='The ARM storage container where the image will be uploaded.'
)
azure_job_message['properties']['source_resource_group'] = string_with_example(
    'res_group1',
    description='The resource group where the source container and source '
                'storage account reside.'
)
azure_job_message['properties']['source_storage_account'] = string_with_example(
    'storage_account1',
    description='The storage account where the source container resides.'
)
azure_job_message['properties']['destination_container'] = string_with_example(
    'container2',
    description='The ASM (legacy) storage container where the image will '
                'be copied to after image has passed testing.'
)
azure_job_message['properties']['destination_resource_group'] = string_with_example(
    'res_group2',
    description='The resource group where the destination container and '
                'destination storage account reside.'
)
azure_job_message['properties']['destination_storage_account'] = string_with_example(
    'storage_account2',
    description='The storage account where the destination container resides.'
)
azure_job_message['properties']['region'] = string_with_example(
    'westus',
    description='The region to use for launching and testing an instance '
                'of the image.'
)

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
