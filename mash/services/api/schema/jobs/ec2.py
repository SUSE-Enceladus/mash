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

from mash.services.api.schema import string_with_example, non_empty_string
from mash.services.api.schema.jobs import base_job_message

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
            description='Region to use for initial image creation and '
                        'test.'
        ),
        'root_swap_ami': string_with_example(
            'ami-1234567890',
            description='The image AMI to use for the root swap image '
                        'creation method.'
        ),
        'subnet': string_with_example(
            'subnet-12345678',
            description='The subnet to use for image test and image '
                        'creation.'
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
ec2_job_message['properties']['share_snapshot_with'] = {
    'type': 'string',
    'format': 'regex',
    'pattern': '^[0-9]{12}(,[0-9]{12})*$',
    'example': '123456789012,098765432109',
    'description': 'A comma-separated list of accounts to share the '
                   'image snapshot with.'
}
ec2_job_message['anyOf'] = [
    {'required': ['cloud_account']},
    {'required': ['cloud_accounts']},
    {'required': ['cloud_groups']}
]
