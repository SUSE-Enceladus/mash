# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

oci_account = {
    'type': 'object',
    'properties': {
        'account_name': string_with_example('account1'),
        'bucket': string_with_example('image-bucket'),
        'region': string_with_example('us-phoenix-1'),
        'availability_domain': string_with_example('Omic:PHX-AD-1'),
        'compartment_id': string_with_example('ocid1.compartment.oc1..'),
        'oci_user_id': string_with_example('ocid1.user.oc1..'),
        'tenancy': string_with_example('ocid1.tenancy.oc1..')
    },
    'additionalProperties': False,
    'required': [
        'account_name',
        'bucket',
        'region',
        'availability_domain',
        'compartment_id',
        'oci_user_id',
        'tenancy'
    ]
}

add_account_oci = copy.deepcopy(oci_account)
add_account_oci['properties']['signing_key'] = string_with_example(
    '-----BEGIN PRIVATE KEY-----{key content}'
)
add_account_oci['required'].append('signing_key')

oci_account_update = {
    'type': 'object',
    'properties': {
        'bucket': string_with_example('image-bucket'),
        'region': string_with_example('us-phoenix-1'),
        'availability_domain': string_with_example('Omic:PHX-AD-1'),
        'compartment_id': string_with_example('ocid1.compartment.oc1..'),
        'oci_user_id': string_with_example('ocid1.user.oc1..'),
        'tenancy': string_with_example('ocid1.tenancy.oc1..'),
        'signing_key': string_with_example(
            '-----BEGIN PRIVATE KEY-----{key content}'
        )
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['bucket']},
        {'required': ['region']},
        {'required': ['availability_domain']},
        {'required': ['compartment_id']},
        {'required': ['oci_user_id']},
        {'required': ['tenancy']},
        {'required': ['signing_key']}
    ]
}
