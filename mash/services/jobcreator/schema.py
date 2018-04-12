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


add_account = {
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
        'provider': {'enum': ['azure', 'ec2']},
        'requesting_user': {'$ref': '#/definitions/non_empty_string'},
    },
    'additionalProperties': False,
    'required': ['account_name', 'credentials', 'provider', 'requesting_user'],
    'definitions': {
        'non_empty_string': {
            'type': 'string',
            'minLength': 1
        }
    }
}
