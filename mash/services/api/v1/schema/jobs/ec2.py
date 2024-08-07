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

from mash.services.api.v1.schema import string_with_example, non_empty_string
from mash.services.api.v1.schema.jobs import base_job_message

ec2_job_account = {
    'type': 'object',
    'properties': {
        'name': string_with_example(
            'account1',
            description='Name of cloud account as associated with the mash '
                        'user account.'
        ),
        'region': string_with_example(
            'us-east-1',
            description='Region to use for initial image creation.'
        ),
        'root_swap_ami': string_with_example(
            'ami-1234567890',
            description='The image AMI to use for the root swap image '
                        'creation method.'
        ),
        'subnet': string_with_example(
            'subnet-12345678',
            description='The subnet to use for image creation.'
        )
    },
    'additionalProperties': False,
    'required': ['name'],
    'description': 'EC2 account credentials to use for the job. '
                   'Name is required and the other properties are '
                   'optional. If supplied region, root_swap_ami and '
                   'subnet will override the account default values.'
}

ec2_job_message = copy.deepcopy(base_job_message)
ec2_job_message['properties']['share_with'] = {
    'type': 'string',
    'format': 'regex',
    'pattern': '^[0-9]{12}(,[0-9]{12})*$|^(all|none)$',
    'example': '123456789012,098765432109',
    'examples': ['all', 'none', '123456789012,098765432109'],
    'description': 'Sharing image to "all" shares the image publicly. '
                   'Sharing to "none" keeps the image private and sharing '
                   'to a comma-separated list of accounts makes it available '
                   'to only those accounts.'
}
ec2_job_message['properties']['allow_copy'] = {
    'type': 'string',
    'format': 'regex',
    'pattern': '^[0-9]{12}(,[0-9]{12})*$|^(image|none)$',
    'example': '123456789012,098765432109',
    'examples': ['image', 'none', '123456789012,098765432109'],
    'description': 'Set the image copy permissions. Supports '
                   'the keyword "image" to allow those that the image is '
                   'shared with to copy it; the keyword "none" which does '
                   'not allow copy access and is the default behavior. And '
                   'an AWS account number or a comma-separated list with no '
                   'white space to specify multiple account numbers to allow '
                   'those accounts to copy the image.'
}
ec2_job_message['properties']['billing_codes'] = string_with_example(
    'bp-1234567890,bp-0987654321',
    description='A comma-separated list of billing codes to apply during '
                'image creation'
)
ec2_job_message['properties']['use_root_swap'] = {
    'type': 'boolean',
    'description': 'Whether to use root swap technique during image '
                   'creation in ec2imgutils package.'
}
ec2_job_message['properties']['cloud_accounts'] = {
    'type': 'array',
    'items': ec2_job_account,
    'minItems': 1,
    'example': [{'name': 'account1', 'region': 'us-east-2'}],
    'description': 'A list of cloud account dictionaries. Either a '
                   'cloud_account, cloud_accounts or cloud_groups is '
                   'required for an EC2 job. This allows the creation and '
                   'test of the same image in multiple partition.'
}
ec2_job_message['properties']['cloud_account'] = string_with_example(
    'account1',
    description='The name of the cloud account to use for '
                'the job. This is mutually exclusive with the '
                '"cloud_accounts" setting.'
)
ec2_job_message['properties']['cloud_groups'] = {
    'type': 'array',
    'items': non_empty_string,
    'uniqueItems': True,
    'minItems': 1,
    'example': ['group1', 'group2'],
    'description': 'A list of cloud groups to use for EC2 credentials. '
                   'Either a cloud_account, cloud_accounts or cloud_groups '
                   'is required for an EC2 job.'
}
ec2_job_message['properties']['skip_replication'] = {
    'type': 'boolean',
    'description': 'Whether to skip the replication step. If true '
                   'the image that is uploaded will not be replicated'
                   'to any regions.'
}
ec2_job_message['properties']['publish_in_marketplace'] = {
    'type': 'boolean',
    'description': 'Whether the image is published in the AWS Marketplace.'
}
ec2_job_message['properties']['entity_id'] = string_with_example(
    '12345678-1234-1234-1234-012345678912',
    description='The marketplace entity identifier. This is expected '
                'to be a UUID format ID.'
)
ec2_job_message['properties']['version_title'] = string_with_example(
    'openSUSE Leap 15.3 - v202220114',
    description='The unique marketplace version title which will be '
                'displayed to end users.'
)
ec2_job_message['properties']['release_notes'] = string_with_example(
    'Information about a new version',
    description='Notes for buyers to tell them about changes from one '
                'version to the next.'
)
ec2_job_message['properties']['access_role_arn'] = string_with_example(
    'arn:aws:iam::123456789012:role/exampleRole',
    description='The access role that provides the AWS Marketplace with '
                '"AMI Assets Ingestion" permissions.'
)
ec2_job_message['properties']['os_name'] = string_with_example(
    'OTHERLINUX',
    description='The name of the operating system for a marketplace image.'
)
ec2_job_message['properties']['os_version'] = string_with_example(
    '15.3',
    description='The operating system version for a marketplace image.'
)
ec2_job_message['properties']['usage_instructions'] = string_with_example(
    'Instructions on image usage...',
    description='Instructions for using the marketplace image.'
)
ec2_job_message['properties']['recommended_instance_type'] = string_with_example(
    't3.medium',
    description='The instance type that is recommended to run the service '
                'with the marketplace image.'
)
ec2_job_message['properties']['tpm_support'] = string_with_example(
    'v2.0',
    description='The NitroTPM version supported by the image.'
)
ec2_job_message['properties']['launch_inst_type'] = string_with_example(
    'm1.large',
    description='The helper instance type to use for image creation with ec2uploadimg.'
)
ec2_job_message['properties']['imds_version'] = string_with_example(
    'v2.0',
    description='Set the protocol version to be used when instances are'
                'launched from the image, supported values 2.0/v2.0. '
)
ec2_job_message['anyOf'] = [
    {'required': ['cloud_account']},
    {'required': ['cloud_accounts']},
    {'required': ['cloud_groups']}
]
