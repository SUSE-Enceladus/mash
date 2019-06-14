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

from mash.services.api.schema import (
    email,
    non_empty_string,
    string_with_example
)

image_conditions = {
    'type': 'object',
    'properties': {
        'image': string_with_example('1.42.1')
    },
    'additionalProperties': False,
    'required': ['image']
}

package_conditions = {
    'type': 'object',
    'properties': {
        'package_name': string_with_example('kernel-default'),
        'version': string_with_example('4.13.1'),
        'build_id': string_with_example('1.1'),
        'condition': {
            'type': 'string',
            'enum': ['>=', '==', '<=', '>', '<']
        }
    },
    'additionalProperties': False,
    'required': ['package_name']
}

utctime = {
    'type': 'string',
    'description': 'An RFC3339 date-time string, "now" or "always"',
    'format': 'regex',
    'pattern': r'^([0-9]+)-(0[1-9]|1[012])-(0[1-9]|[12][0-9]'
               r'|3[01])[Tt]([01][0-9]|2[0-3]):([0-5][0-9]):'
               r'([0-5][0-9]|60)(\.[0-9]+)?(([Zz])|([\+|\-]'
               r'([01][0-9]|2[0-3]):[0-5][0-9]))$|^(now|always)$',
    'example': '2019-04-28T06:44:50.142Z',
    'examples': ['now', 'always', '2019-04-28T06:44:50.142Z']
}

base_job_message = {
    'type': 'object',
    'properties': {
        'cloud_groups': {
            'type': 'array',
            'items': non_empty_string,
            'uniqueItems': True,
            'minItems': 1,
            'example': ['group1']
        },
        'requesting_user': string_with_example('user123'),
        'last_service': {
            'type': 'string',
            'enum': [
                'uploader',
                'testing',
                'replication',
                'publisher',
                'deprecation'
            ]
        },
        'utctime': utctime,
        'image': string_with_example('openSUSE-Leap-15.0-EC2-HVM'),
        'cloud_image_name': string_with_example(
            'openSUSE-Leap-15.0-v{date}-hvm-ssd-x86_64'
        ),
        'old_cloud_image_name': string_with_example(
            'openSUSE-Leap-15.0-v20190313-hvm-ssd-x86_64'
        ),
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
        'download_url': string_with_example(
            'https://download.opensuse.org/repositories/'
            'Cloud:/Images:/Leap_15.0/images/'
        ),
        'image_description': string_with_example(
            'openSUSE Leap 15.0 (HVM, 64-bit, SSD-Backed)'
        ),
        'distro': {
            'type': 'string',
            'enum': ['opensuse_leap', 'sles']
        },
        'instance_type': string_with_example('t2.micro'),
        'tests': {
            'type': 'array',
            'items': non_empty_string,
            'minItems': 1,
            'example': ['test_sles']
        },
        'cleanup_images': {'type': 'boolean'},
        'cloud_architecture': {
            'type': 'string',
            'enum': ['x86_64', 'aarch64']
        },
        'notification_email': email,
        'notification_type': {
            'type': 'string',
            'enum': ['periodic', 'single']
        }
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['cloud_accounts']},
        {'required': ['cloud_groups']}
    ],
    'required': [
        'requesting_user',
        'last_service',
        'utctime',
        'image',
        'cloud_image_name',
        'image_description',
        'download_url'
    ]
}
