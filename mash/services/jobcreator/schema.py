# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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


non_empty_string = {
    'type': 'string',
    'minLength': 1
}


add_account_ec2 = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'credentials': {
            'type': 'object',
            'properties': {
                'access_key_id': {'$ref': '#/definitions/non_empty_string'},
                'secret_access_key': {'$ref': '#/definitions/non_empty_string'}
            },
            'additionalProperties': False
        },
        'group': {'$ref': '#/definitions/non_empty_string'},
        'partition': {'$ref': '#/definitions/non_empty_string'},
        'provider': {'enum': ['ec2']},
        'requesting_user': {'$ref': '#/definitions/non_empty_string'},
    },
    'additionalProperties': False,
    'required': ['account_name', 'credentials', 'provider', 'requesting_user'],
    'definitions': {
        'non_empty_string': non_empty_string
    }
}


delete_account_ec2 = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'provider': {'enum': ['ec2']},
        'requesting_user': {'$ref': '#/definitions/non_empty_string'},
    },
    'additionalProperties': False,
    'required': ['account_name', 'provider', 'requesting_user'],
    'definitions': {
        'non_empty_string': non_empty_string
    }
}


base_job_message = {
    'type': 'object',
    'properties': {
        'provider_accounts': {
            'type': 'array',
            'items': {'$ref': '#definitions/account'}
        },
        'provider_groups': {
            'type': 'array',
            'items': {'$ref': '#/definitions/non_empty_string'},
            'uniqueItems': True
        },
        'requesting_user': {'$ref': '#/definitions/non_empty_string'},
        'last_service': {
            'enum': [
                'obs', 'uploader', 'testing', 'replication',
                'publisher', 'deprecation', 'pint'
            ]
        },
        'utctime': {
            'anyOf': [
                {'enum': ['always', 'now']},
                {
                    '$ref': '#/definitions/non_empty_string',
                    'format': 'date-time'
                }
            ]
        },
        'image': {'$ref': '#/definitions/non_empty_string'},
        'cloud_image_name': {'$ref': '#/definitions/non_empty_string'},
        'old_cloud_image_name': {'$ref': '#/definitions/non_empty_string'},
        'project': {'$ref': '#/definitions/non_empty_string'},
        'conditions': {
            'type': 'array',
            'items': {
                'anyOf': [
                    {'$ref': '#definitions/image_conditions'},
                    {'$ref': '#definitions/package_conditions'}
                ]
            },
            'minItems': 1
        },
        'image_description': {'$ref': '#/definitions/non_empty_string'},
        'distro': {'$ref': '#/definitions/non_empty_string'},
        'instance_type': {'$ref': '#/definitions/non_empty_string'},
        'tests': {
            'type': 'array',
            'items': {'$ref': '#/definitions/non_empty_string'},
            'minItems': 1
        }
    },
    'additionalProperties': False,
    'required': [
        'provider', 'provider_accounts', 'provider_groups', 'requesting_user',
        'last_service', 'utctime', 'image', 'cloud_image_name',
        'old_cloud_image_name', 'project', 'image_description', 'tests'
    ],
    'definitions': {
        'image_conditions': {
            'properties': {
                'image': {'$ref': '#/definitions/non_empty_string'}
            },
            'additionalProperties': False,
            'required': ['image']
        },
        'non_empty_string': non_empty_string,
        'package_conditions': {
            'properties': {
                'package': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/non_empty_string'},
                    'minItems': 2
                }
            },
            'additionalProperties': False,
            'required': ['package']
        }
    }
}

ec2_job_message = copy.deepcopy(base_job_message)
ec2_job_message['properties']['provider'] = {'enum': ['ec2']}
ec2_job_message['properties']['share_with'] = {
    'anyOf': [
        {'enum': ['all', 'none']},
        {
            '$ref': '#/definitions/non_empty_string',
            'format': 'regex',
            'pattern': '^[0-9]{12}(,[0-9]{12})*$'
        }
    ]
}
ec2_job_message['properties']['allow_copy'] = {'type': 'boolean'}
ec2_job_message['required'] += ['share_with', 'allow_copy']
ec2_job_message['definitions']['account'] = {
    'properties': {
        'name': {'$ref': '#/definitions/non_empty_string'},
        'target_regions': {
            'type': 'array',
            'items': {'$ref': '#/definitions/non_empty_string'},
            'uniqueItems': True
        }
    },
    'additionalProperties': False,
    'required': ['name', 'target_regions']
}


azure_job_message = copy.deepcopy(base_job_message)
azure_job_message['properties']['provider'] = {'enum': ['azure']}
azure_job_message['definitions']['account'] = {
    'properties': {
        'name': {'$ref': '#/definitions/non_empty_string'},
        'region': {'$ref': '#/definitions/non_empty_string'},
        'resource_group': {'$ref': '#/definitions/non_empty_string'},
        'container_name': {'$ref': '#/definitions/non_empty_string'},
        'storage_account': {'$ref': '#/definitions/non_empty_string'}
    },
    'additionalProperties': False,
    'required': ['name']
}
