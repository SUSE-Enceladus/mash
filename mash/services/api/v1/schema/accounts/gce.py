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

from mash.services.api.v1.schema import string_with_example

gce_account = {
    'type': 'object',
    'properties': {
        'account_name': string_with_example('account1'),
        'bucket': string_with_example('image-bucket'),
        'testing_account': string_with_example('test-account1'),
        'region': string_with_example('us-west1-a'),
        'is_publishing_account': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'bucket',
        'region'
    ]
}

gce_credentials = {
    'type': 'object',
    'properties': {
        'type': string_with_example('service_account'),
        'project_id': string_with_example('test'),
        'private_key_id': string_with_example(
            '1234567890123456789012345678901234567890'
        ),
        'private_key': string_with_example(
            '-----BEGIN PRIVATE KEY-----{key content}'
        ),
        'client_email': string_with_example(
            'test@test.iam.gserviceaccount.com'
        ),
        'client_id': string_with_example(
            '123456789012345678901'
        ),
        'auth_uri': string_with_example(
            'https://accounts.google.com/o/oauth2/auth'
        ),
        'token_uri': string_with_example(
            'https://accounts.google.com/o/oauth2/auth'
        ),
        'auth_provider_x509_cert_url': string_with_example(
            'https://www.googleapis.com/oauth2/v1/certs'
        ),
        'client_x509_cert_url': string_with_example(
            'https://www.googleapis.com/robot/v1/metadata/x509/'
            'test@test.iam.gserviceaccount.com'
        ),
        'universe_domain': string_with_example(
            'googleapis.com'
        )
    },
    'additionalProperties': False,
    'required': [
        'type',
        'project_id',
        'private_key_id',
        'private_key',
        'client_email',
        'client_id',
        'auth_uri',
        'token_uri',
        'auth_provider_x509_cert_url',
        'client_x509_cert_url'
    ]
}

add_account_gce = copy.deepcopy(gce_account)
add_account_gce['properties']['credentials'] = gce_credentials
add_account_gce['required'].append('credentials')

gce_account_update = {
    'type': 'object',
    'properties': {
        'bucket': string_with_example('image-bucket'),
        'testing_account': string_with_example('test-account1'),
        'region': string_with_example('us-west1-a'),
        'credentials': gce_credentials
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['bucket']},
        {'required': ['testing_account']},
        {'required': ['region']},
        {'required': ['credentials']}
    ]
}
