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


job_message = {
    'type': 'object',
    'properties': {
        'provider': {'enum': ['azure', 'ec2']},
        'provider_accounts': {
            'type': 'array',
            'items': {'$ref': '#/definitions/non_empty_string'},
            'uniqueItems': True,
            'minItems': 1
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
        'share_with': {
            'anyOf': [
                {'enum': ['all', 'none']},
                {
                    '$ref': '#/definitions/non_empty_string',
                    'format': 'regex',
                    'pattern': '^[0-9]{12}(,[0-9]{12})*$'
                }
            ]
        },
        'allow_copy': {'type': 'boolean'},
        'image_description': {'$ref': '#/definitions/non_empty_string'},
        'target_regions': {
            'type': 'object',
            'properties': {
                'accounts': {
                    'type': 'array',
                    'items': {'$ref': '#definitions/account'}
                },
                'groups': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/non_empty_string'},
                    'uniqueItems': True
                }
            }
        },
        'tests': {
            'type': 'array',
            'items': {'$ref': '#/definitions/non_empty_string'},
            'minItems': 1
        }
    },
    'additionalProperties': False,
    'required': [
        'provider', 'provider_accounts', 'requesting_user', 'last_service',
        'utctime', 'image', 'cloud_image_name', 'old_cloud_image_name',
        'project', 'share_with', 'allow_copy', 'image_description',
        'target_regions', 'tests'
    ],
    'definitions': {
        'account': {
            'properties': {
                'name': {'$ref': '#/definitions/non_empty_string'},
                'regions': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/non_empty_string'},
                    'uniqueItems': True
                }
            },
            'additionalProperties': False,
            'required': ['name']
        },
        'image_conditions': {
            'properties': {
                'image': {'$ref': '#/definitions/non_empty_string'}
            },
            'additionalProperties': False,
            'required': ['image']
        },
        'non_empty_string': {
            'type': 'string',
            'minLength': 1
        },
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
