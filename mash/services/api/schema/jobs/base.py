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

from mash.services.api.schema.base import (
    email,
    non_empty_string,
    utctime
)

image_conditions = {
    'properties': {
        'image': non_empty_string
    },
    'additionalProperties': False,
    'required': ['image']
}

package_conditions = {
    'properties': {
        'package_name': non_empty_string,
        'version': non_empty_string,
        'build_id': non_empty_string,
        'condition': {
            'enum': ['>=', '==', '<=', '>', '<']
        }
    },
    'additionalProperties': False,
    'required': ['package_name']
}

base_job_message = {
    'type': 'object',
    'properties': {
        'cloud_groups': {
            'type': 'array',
            'items': non_empty_string,
            'uniqueItems': True,
            'minItems': 1
        },
        'requesting_user': non_empty_string,
        'last_service': {
            'enum': [
                'uploader',
                'testing',
                'replication',
                'publisher',
                'deprecation'
            ]
        },
        'utctime': {
            'anyOf': [
                {'enum': ['always', 'now']},
                utctime
            ]
        },
        'image': non_empty_string,
        'cloud_image_name': non_empty_string,
        'old_cloud_image_name': non_empty_string,
        'conditions': {
            'type': 'array',
            'items': {
                'anyOf': [
                    image_conditions,
                    package_conditions
                ]
            },
            'minItems': 1
        },
        'download_url': non_empty_string,
        'image_description': non_empty_string,
        'distro': {'enum': ['opensuse_leap', 'sles']},
        'instance_type': non_empty_string,
        'tests': {
            'type': 'array',
            'items': non_empty_string,
            'minItems': 1
        },
        'cleanup_images': {'type': 'boolean'},
        'cloud_architecture': {
            'enum': ['x86_64', 'aarch64']
        },
        'notification_email': email,
        'notification_type': {
            'enum': ['periodic', 'single']
        }
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['cloud_accounts']},
        {'required': ['cloud_groups']}
    ],
    'required': [
        'cloud',
        'requesting_user',
        'last_service',
        'utctime',
        'image',
        'cloud_image_name',
        'image_description',
        'download_url'
    ]
}
