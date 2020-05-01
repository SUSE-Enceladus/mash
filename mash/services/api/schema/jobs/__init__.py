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

image_condition = {
    'type': 'object',
    'properties': {
        'package_name': string_with_example(
            'kernel-default',
            description='The name of the package for this condition. '
                        'If no name is provided for a condition then the '
                        'condition is checked against the image itself.'
        ),
        'version': string_with_example(
            '4.13.1',
            description='The package or image version from the build service.'
                        ' If no package_name is provided with the condition '
                        'then the condition is against the image.'
        ),
        'release': string_with_example(
            '1.1',
            description='The build (release) number for the package or image.'
                        ' If no package_name is provided with the condition '
                        'then the condition is against the image.'
        ),
        'condition': {
            'type': 'string',
            'enum': ['>=', '==', '<=', '>', '<'],
            'example': '==',
            'description': 'The expression to use for comparing version '
                           'and/or release.'
        }
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['package_name']},
        {'required': ['version']},
        {'required': ['release']}
    ]
}

utctime = {
    'type': 'string',
    'description': 'An RFC3339 date-time string, "now" or "always".'
                   'If using a date string it must be in the future '
                   'and the job will start no sooner than the provided '
                   'date. Now jobs will run as soon as possible and always '
                   'jobs run through the pipeline every time a new image '
                   'tarball is published.',
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
        'last_service': {
            'type': 'string',
            'enum': [
                'uploader',
                'create',
                'testing',
                'raw_image_uploader',
                'replication',
                'publisher',
                'deprecation'
            ],
            'example': 'create',
            'description': 'The last service in the pipeline to be executed. '
                           'All services except the OBS service are valid '
                           'values.'
        },
        'utctime': utctime,
        'image': string_with_example(
            'openSUSE-Leap-15.0-EC2-HVM',
            description='This should match the name of the tarball file on'
                        'the download server prior to the architecture. For '
                        'a file like openSUSE-Leap-15.0-EC2-HVM.x86_64-1.0.0-'
                        'Build1.206.vhdfixed.xz.sha256 The "image" is '
                        'openSUSE-Leap-15.0-EC2-HVM.'
        ),
        'cloud_image_name': string_with_example(
            'openSUSE-Leap-15.0-v{date}-hvm-ssd-x86_64',
            description='The name to use for the uploaded image in the cloud '
                        'framework. The name can have a date of upload '
                        'inserted such as the example. The {date} will be '
                        'replaced by the current iso date format at time of '
                        'upload (20200410).'
        ),
        'old_cloud_image_name': string_with_example(
            'openSUSE-Leap-15.0-v20190313-hvm-ssd-x86_64',
            description='The cloud image name for the image to be deprecated. '
                        'This is only required for jobs that run through '
                        'deprecation service.'
        ),
        'conditions': {
            'type': 'array',
            'items': image_condition,
            'minItems': 1,
            'example': [
                {
                    'package_name': 'kernel-default',
                    'version': '4.13.1',
                    'condition': '>='
                }
            ],
            'description': 'A list of image conditions to check the image '
                           'against. Providing only the package name will '
                           'ensure the package is in the image. The version '
                           'is the package version from the build service '
                           'whereas the release is the build or release '
                           'number. At least one of package_name, version or '
                           'release is required. If no package name is '
                           'provided then the condition is against the image '
                           'itself. Valid condition operators are >, <, >=, '
                           '<=, or ==.'
        },
        'download_url': string_with_example(
            'https://download.opensuse.org/repositories/'
            'Cloud:/Images:/Leap_15.0/images/',
            description='The URL to a download repository. The URL is '
                        'expected to have the image tarball, checksum and '
                        'a packages file.'
        ),
        'image_description': string_with_example(
            'openSUSE Leap 15.0 (HVM, 64-bit, SSD-Backed)',
            description='Description to use when creating the image in the '
                        'cloud framework.'
        ),
        'distro': {
            'type': 'string',
            'enum': ['opensuse_leap', 'sles'],
            'example': 'sles',
            'description': 'The distribution setting used for the img-proof '
                           'tests.'
        },
        'instance_type': string_with_example(
            't2.micro',
            description='Instance size/type img-proof will use when '
                        'launching a test instance. If no type is provided '
                        'a random type will be selected from a pre-configured '
                        'list.'
        ),
        'tests': {
            'type': 'array',
            'items': non_empty_string,
            'minItems': 1,
            'example': ['test_sles'],
            'description': 'This is a list of img-proof tests or test '
                           'descriptions. The tests will be run against '
                           'the instance. If any tests fail the job will '
                           'fail.'
        },
        'cleanup_images': {
            'type': 'boolean',
            'example': True,
            'description': 'Whether to cleanup the image artifacts. By '
                           'default all artifacts are cleaned up when the '
                           'last service is testing or if a publishing job '
                           'fails.'
        },
        'cloud_architecture': {
            'type': 'string',
            'enum': ['x86_64', 'aarch64'],
            'example': 'x86_64',
            'description': 'The underlying architecture for the image. '
                           'Valid options are x86_64 and aarch64 and the '
                           'default architecture is x86_64.'
        },
        'notification_email': email,
        'notification_type': {
            'type': 'string',
            'enum': ['periodic', 'single'],
            'example': 'single',
            'description': 'The single notification option sends an email '
                           'with job status when the job finishes or fails. '
                           'The periodic option will send an email after the '
                           'job finishes each service with the job status.'
        },
        'profile': string_with_example('Proxy'),
        'conditions_wait_time': {
            'type': 'integer',
            'minimum': 0,
            'example': 900,
            'description': 'The time (in seconds) to wait before failing '
                           'a job on image conditions.'
        },
        'raw_image_upload_type': string_with_example(
            's3bucket',
            description='Cloud framework to use for raw image tarball '
                        'upload. The image tarball will be uploaded as is '
                        'to the framework using the cloud image name.'
        ),
        'raw_image_upload_location': string_with_example(
            'my-bucket/prefix/',
            description='The location to put the raw image. This is '
                        'dependent on the cloud framework chosen. For '
                        'example an S3 upload format would be '
                        '{bucket_name}/{prefix}/ to denote the bucket and '
                        'a prefix where the image should be uploaded.'
        ),
        'raw_image_upload_account': string_with_example(
            'my_aws_account',
            description='The cloud framework account as configured with '
                        'the mash account add client command when the mash '
                        'user was setup. The credentials associated with '
                        'this cloud framework account will be used for the '
                        'raw image upload.'
        ),
        'disallow_licenses': {
            'type': 'array',
            'items': non_empty_string,
            'minItems': 1,
            'example': ['MIT'],
            'description': 'A list of licenses that should not be in the '
                           'image. If a package is in the manifest that has '
                           'a matching license the job will fail.'
        },
        'disallow_packages': {
            'type': 'array',
            'items': non_empty_string,
            'minItems': 1,
            'example': ['*-mini'],
            'description': 'A list of packages that should not be in the '
                           'image. If a package is in the manifest that has '
                           'a matching name the job will fail. The * wildcard '
                           'can be used to match a package name pattern.'
        },
        'boot_firmware': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': ['bios', 'uefi'],
            },
            'example': ['bios'],
            'description': 'A list of boot firmware settings to test the '
                           'image with. The default value if left empty is '
                           'bios only. If both bios and uefi are provided '
                           'the image is tested once for each firmware '
                           'setting.'
        },
    },
    'additionalProperties': False,
    'required': [
        'last_service',
        'utctime',
        'image',
        'cloud_image_name',
        'image_description',
        'download_url'
    ]
}
