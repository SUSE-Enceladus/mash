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


non_empty_string = {
    'type': 'string',
    'minLength': 1
}


add_account_azure = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'credentials': {
            'type': 'object',
            'properties': {
                'clientId': non_empty_string,
                'clientSecret': non_empty_string,
                'subscriptionId': non_empty_string,
                'tenantId': non_empty_string,
                'activeDirectoryEndpointUrl': non_empty_string,
                'resourceManagerEndpointUrl': non_empty_string,
                'activeDirectoryGraphResourceId': non_empty_string,
                'sqlManagementEndpointUrl': non_empty_string,
                'galleryEndpointUrl': non_empty_string,
                'managementEndpointUrl': non_empty_string
            },
            'additionalProperties': True,
            'required': [
                'clientId', 'clientSecret', 'subscriptionId', 'tenantId',
                'activeDirectoryEndpointUrl', 'resourceManagerEndpointUrl',
                'activeDirectoryGraphResourceId', 'sqlManagementEndpointUrl',
                'galleryEndpointUrl', 'managementEndpointUrl'
            ],
        },
        'group': non_empty_string,
        'cloud': {'enum': ['azure']},
        'region': non_empty_string,
        'requesting_user': non_empty_string,
        'source_container': non_empty_string,
        'source_resource_group': non_empty_string,
        'source_storage_account': non_empty_string,
        'destination_container': non_empty_string,
        'destination_resource_group': non_empty_string,
        'destination_storage_account': non_empty_string
    },
    'additionalProperties': False,
    'required': [
        'account_name', 'credentials', 'cloud', 'requesting_user',
        'source_container', 'source_resource_group', 'source_storage_account',
        'destination_container', 'destination_resource_group',
        'destination_storage_account'
    ]
}


add_account_ec2 = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'additional_regions': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': non_empty_string,
                    'helper_image': non_empty_string
                },
                'required': ['name', 'helper_image'],
                'additionalProperties': False
            },
            'minItems': 1
        },
        'credentials': {
            'type': 'object',
            'properties': {
                'access_key_id': non_empty_string,
                'secret_access_key': non_empty_string
            },
            'additionalProperties': False,
            'required': ['access_key_id', 'secret_access_key']
        },
        'group': non_empty_string,
        'partition': non_empty_string,
        'region': non_empty_string,
        'cloud': {'enum': ['ec2']},
        'requesting_user': non_empty_string,
    },
    'additionalProperties': False,
    'required': [
        'account_name', 'credentials', 'cloud', 'requesting_user', 'region'
    ]
}


add_account_gce = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'bucket': non_empty_string,
        'credentials': {
            'type': 'object',
            'properties': {
                'type': non_empty_string,
                'project_id': non_empty_string,
                'private_key_id': non_empty_string,
                'private_key': non_empty_string,
                'client_email': non_empty_string,
                'client_id': non_empty_string,
                'auth_uri': non_empty_string,
                'token_uri': non_empty_string,
                'auth_provider_x509_cert_url': non_empty_string,
                'client_x509_cert_url': non_empty_string
            },
            'additionalProperties': False,
            'required': [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri',
                'auth_provider_x509_cert_url', 'client_x509_cert_url'
            ]
        },
        'group': non_empty_string,
        'cloud': {'enum': ['gce']},
        'testing_account': non_empty_string,
        'region': non_empty_string,
        'requesting_user': non_empty_string,
        'is_publishing_account': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': [
        'account_name', 'bucket', 'credentials', 'cloud',
        'requesting_user', 'region'
    ]
}


delete_account = {
    'type': 'object',
    'properties': {
        'account_name': non_empty_string,
        'cloud': {'enum': ['azure', 'ec2', 'gce']},
        'requesting_user': non_empty_string,
    },
    'additionalProperties': False,
    'required': ['account_name', 'cloud', 'requesting_user']
}


base_job_message = {
    'type': 'object',
    'properties': {
        'cloud_accounts': {
            'type': 'array',
            'items': {'$ref': '#definitions/account'},
            'minItems': 1
        },
        'cloud_groups': {
            'type': 'array',
            'items': non_empty_string,
            'uniqueItems': True,
            'minItems': 1
        },
        'requesting_user': non_empty_string,
        'last_service': {
            'enum': [
                'uploader', 'testing', 'replication',
                'publisher', 'deprecation'
            ]
        },
        'utctime': {
            'anyOf': [
                {'enum': ['always', 'now']},
                {
                    'type': 'string',
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
        'image': non_empty_string,
        'cloud_image_name': non_empty_string,
        'old_cloud_image_name': non_empty_string,
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
        'notification_email': {
            'type': 'string',
            'format': 'regex',
            'pattern': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        },
        'notification_type': {
            'enum': ['periodic', 'single']
        },
        'profile': {'$ref': '#/definitions/non_empty_string'}
    },
    'additionalProperties': False,
    'anyOf': [
        {'required': ['cloud_accounts']}, {'required': ['cloud_groups']}
    ],
    'required': [
        'cloud', 'requesting_user',
        'last_service', 'utctime', 'image', 'cloud_image_name',
        'image_description', 'download_url'
    ],
    'definitions': {
        'image_conditions': {
            'properties': {
                'image': non_empty_string
            },
            'additionalProperties': False,
            'required': ['image']
        },
        'package_conditions': {
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
    }
}

ec2_job_message = copy.deepcopy(base_job_message)
ec2_job_message['properties']['cloud'] = {'enum': ['ec2']}
ec2_job_message['properties']['share_with'] = {
    'anyOf': [
        {'enum': ['all', 'none']},
        {
            'type': 'string',
            'format': 'regex',
            'pattern': '^[0-9]{12}(,[0-9]{12})*$'
        }
    ]
}
ec2_job_message['properties']['allow_copy'] = {'type': 'boolean'}
ec2_job_message['properties']['billing_codes'] = non_empty_string
ec2_job_message['properties']['use_root_swap'] = {'type': 'boolean'}
ec2_job_message['definitions']['account'] = {
    'type': 'object',
    'properties': {
        'name': non_empty_string,
        'region': non_empty_string,
        'root_swap_ami': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}


azure_job_message = copy.deepcopy(base_job_message)
azure_job_message['properties']['cloud'] = {'enum': ['azure']}
azure_job_message['properties']['emails'] = non_empty_string
azure_job_message['properties']['label'] = non_empty_string
azure_job_message['properties']['offer_id'] = non_empty_string
azure_job_message['properties']['publisher_id'] = non_empty_string
azure_job_message['properties']['sku'] = non_empty_string
azure_job_message['properties']['vm_images_key'] = non_empty_string
azure_job_message['properties']['publish_offer'] = {'type': 'boolean'}
azure_job_message['required'].append('emails')
azure_job_message['required'].append('label')
azure_job_message['required'].append('offer_id')
azure_job_message['required'].append('publisher_id')
azure_job_message['required'].append('sku')
azure_job_message['definitions']['account'] = {
    'type': 'object',
    'properties': {
        'name': non_empty_string,
        'region': non_empty_string,
        'source_container': non_empty_string,
        'source_resource_group': non_empty_string,
        'source_storage_account': non_empty_string,
        'destination_container': non_empty_string,
        'destination_resource_group': non_empty_string,
        'destination_storage_account': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}


gce_job_message = copy.deepcopy(base_job_message)
gce_job_message['properties']['cloud'] = {'enum': ['gce']}
gce_job_message['properties']['family'] = non_empty_string
gce_job_message['properties']['months_to_deletion'] = {
    'type': 'integer',
    'minimum': 0
}
gce_job_message['properties']['guest_os_features'] = {
    'type': 'array',
    'items': non_empty_string,
    'uniqueItems': True,
    'minItems': 1
}
gce_job_message['properties']['test_fallback_regions'] = {
    'type': 'array',
    'items': non_empty_string,
    'minItems': 0
}
gce_job_message['properties']['testing_account'] = non_empty_string
gce_job_message['definitions']['account'] = {
    'type': 'object',
    'properties': {
        'bucket': non_empty_string,
        'name': non_empty_string,
        'region': non_empty_string
    },
    'additionalProperties': False,
    'required': ['name']
}
