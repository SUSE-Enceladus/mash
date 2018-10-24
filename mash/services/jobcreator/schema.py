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


add_account_azure = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'container_name': {'$ref': '#/definitions/non_empty_string'},
        'credentials': {
            'type': 'object',
            'properties': {
                'clientId': {'$ref': '#/definitions/non_empty_string'},
                'clientSecret': {'$ref': '#/definitions/non_empty_string'},
                'subscriptionId': {'$ref': '#/definitions/non_empty_string'},
                'tenantId': {'$ref': '#/definitions/non_empty_string'}
            },
            'additionalProperties': True,
            'required': [
                'clientId', 'clientSecret', 'subscriptionId', 'tenantId'
            ],
        },
        'group': {'$ref': '#/definitions/non_empty_string'},
        'provider': {'enum': ['azure']},
        'region': {'$ref': '#/definitions/non_empty_string'},
        'requesting_user': {'$ref': '#/definitions/non_empty_string'},
        'resource_group': {'$ref': '#/definitions/non_empty_string'},
        'storage_account': {'$ref': '#/definitions/non_empty_string'}
    },
    'additionalProperties': False,
    'required': [
        'account_name', 'container_name', 'credentials', 'provider',
        'requesting_user', 'resource_group', 'storage_account'
    ],
    'definitions': {
        'non_empty_string': non_empty_string
    }
}


add_account_ec2 = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'additional_regions': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'$ref': '#/definitions/non_empty_string'},
                    'helper_image': {'$ref': '#/definitions/non_empty_string'}
                },
                'required': ['name', 'helper_image'],
                'additionalProperties': False
            },
            'minItems': 1
        },
        'credentials': {
            'type': 'object',
            'properties': {
                'access_key_id': {'$ref': '#/definitions/non_empty_string'},
                'secret_access_key': {'$ref': '#/definitions/non_empty_string'}
            },
            'additionalProperties': False,
            'required': ['access_key_id', 'secret_access_key']
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


add_account_gce = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'bucket': {'$ref': '#/definitions/non_empty_string'},
        'credentials': {
            'type': 'object',
            'properties': {
                'type': {'$ref': '#/definitions/non_empty_string'},
                'project_id': {'$ref': '#/definitions/non_empty_string'},
                'private_key_id': {'$ref': '#/definitions/non_empty_string'},
                'private_key': {'$ref': '#/definitions/non_empty_string'},
                'client_email': {'$ref': '#/definitions/non_empty_string'},
                'client_id': {'$ref': '#/definitions/non_empty_string'},
                'auth_uri': {'$ref': '#/definitions/non_empty_string'},
                'token_uri': {'$ref': '#/definitions/non_empty_string'},
                'auth_provider_x509_cert_url': {
                    '$ref': '#/definitions/non_empty_string'
                },
                'client_x509_cert_url': {
                    '$ref': '#/definitions/non_empty_string'
                }
            },
            'additionalProperties': False,
            'required': [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri',
                'auth_provider_x509_cert_url', 'client_x509_cert_url'
            ]
        },
        'group': {'$ref': '#/definitions/non_empty_string'},
        'provider': {'enum': ['gce']},
        'region': {'$ref': '#/definitions/non_empty_string'},
        'requesting_user': {'$ref': '#/definitions/non_empty_string'}
    },
    'additionalProperties': False,
    'required': [
        'account_name', 'bucket', 'credentials', 'provider',
        'requesting_user', 'region'
    ],
    'definitions': {
        'non_empty_string': non_empty_string
    }
}


delete_account = {
    'type': 'object',
    'properties': {
        'account_name': {'$ref': '#/definitions/non_empty_string'},
        'provider': {'enum': ['azure', 'ec2']},
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
                    'description': 'An RFC3339 date-time string'
                                   '(2019-04-28T06:44:50.142Z)',
                    'format': 'regex',
                    'pattern': r'^([0-9]+)-(0[1-9]|1[012])-(0[1-9]|[12][0-9]'
                               r'|3[01])[Tt]([01][0-9]|2[0-3]):([0-5][0-9]):'
                               r'([0-5][0-9]|60)(\.[0-9]+)?(([Zz])|([\+|\-]'
                               r'([01][0-9]|2[0-3]):[0-5][0-9]))$'
                }
            ]
        },
        'image': {'$ref': '#/definitions/non_empty_string'},
        'cloud_image_name': {'$ref': '#/definitions/non_empty_string'},
        'old_cloud_image_name': {'$ref': '#/definitions/non_empty_string'},
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
        'download_url': {'$ref': '#/definitions/non_empty_string'},
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
        'old_cloud_image_name', 'image_description', 'download_url', 'tests'
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


gce_job_message = copy.deepcopy(base_job_message)
gce_job_message['properties']['provider'] = {'enum': ['gce']}
gce_job_message['properties']['family'] = {
    '$ref': '#/definitions/non_empty_string'
}
gce_job_message['definitions']['account'] = {
    'properties': {
        'bucket': {'$ref': '#/definitions/non_empty_string'},
        'name': {'$ref': '#/definitions/non_empty_string'},
        'region': {'$ref': '#/definitions/non_empty_string'}
    },
    'additionalProperties': False,
    'required': ['name']
}
