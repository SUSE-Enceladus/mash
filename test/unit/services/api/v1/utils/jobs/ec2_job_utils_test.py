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

from unittest.mock import patch, Mock

from pytest import raises

from mash.mash_exceptions import MashJobException
from mash.services.api.v1.utils.jobs.ec2 import (
    get_ec2_regions_by_partition,
    add_target_ec2_account,
    convert_account_dict,
    validate_ec2_job
)

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
def test_get_ec2_regions_by_partition(mock_get_current_object):
    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {
        'CLOUD_DATA': {
            'ec2': {
                'regions': {
                    'aws': ['us-east-99']
                }
            }
        }
    }

    assert get_ec2_regions_by_partition('aws') == ['us-east-99']


@patch('mash.services.api.v1.utils.jobs.ec2.get_ec2_regions_by_partition')
def test_add_target_ec2_account(mock_get_regions):
    account = {
        'region': 'us-east-100',
        'name': 'acnt1',
        'partition': 'aws',
        'subnet': 'subnet-222222',
        'additional_regions': [
            {
                'name': 'us-east-101',
                # Deprecated and ignored, may be missing
                'helper_image': 'ami-987'
            },
            {
                'name': 'us-east-102'
            }
        ],
        'test_regions': [
            {
                'subnet': 'subnet-111111',
                'region': 'us-east-100'
            }
        ]
    }

    mock_get_regions.return_value = ['us-east-99']

    cloud_accounts = {'acnt1': {}}
    accounts = {}

    add_target_ec2_account(account, accounts, cloud_accounts)

    assert accounts['us-east-100'] == {
        'account': 'acnt1',
        'partition': 'aws',
        'target_regions': accounts['us-east-100']['target_regions'],
        'helper_image': None,
        'subnet': 'subnet-222222',
        'test_regions': account['test_regions']
    }
    assert sorted(accounts['us-east-100']['target_regions']) == [
        'us-east-101', 'us-east-102', 'us-east-99'
    ]

    # Region and subnet override from the job doc
    accounts = {}
    add_target_ec2_account(
        account,
        accounts,
        {'acnt1': {'region': 'us-east-103', 'subnet': 'subnet-333333'}}
    )
    assert accounts['us-east-103']['subnet'] == 'subnet-333333'

    # Root swap uses the root swap AMI of the job doc as donor image
    accounts = {}
    add_target_ec2_account(
        account,
        accounts,
        {'acnt1': {'root_swap_ami': 'ami-456'}},
        use_root_swap=True
    )
    assert accounts['us-east-100']['helper_image'] == 'ami-456'

    # Root swap without root swap AMI
    with raises(MashJobException):
        add_target_ec2_account(
            account,
            {},
            cloud_accounts,
            use_root_swap=True
        )

    # The root swap AMI is ignored without root swap
    accounts = {}
    add_target_ec2_account(
        account,
        accounts,
        {'acnt1': {'root_swap_ami': 'ami-456'}}
    )
    assert accounts['us-east-100']['helper_image'] is None

    accounts = {}
    add_target_ec2_account(
        account,
        accounts,
        cloud_accounts,
        skip_replication=True
    )

    assert accounts['us-east-100']['target_regions'] == ['us-east-100']
    assert accounts['us-east-100']['test_regions'] == account['test_regions']


def test_convert_account_dict():
    accounts = [{'name': 'acnt1', 'data': 'more_stuff'}]
    assert convert_account_dict(accounts)['acnt1']['data'] == 'more_stuff'


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.v1.utils.jobs.ec2.add_target_ec2_account')
@patch('mash.services.api.v1.utils.jobs.ec2.get_ec2_account')
@patch('mash.services.api.v1.utils.jobs.ec2.get_accounts_in_ec2_group')
def test_validate_ec2_job(
    mock_get_group_accounts,
    mock_get_ec2_account,
    mock_add_target_account,
    mock_get_current_obj
):
    account = {
        'region': 'us-east-100',
        'name': 'acnt1',
        'partition': 'aws',
        'additional_regions': [
            {
                'name': 'us-east-100'
            }
        ]
    }
    mock_get_ec2_account.return_value = account
    mock_get_group_accounts.return_value = [account]

    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'download',
            'uploader',
            'create',
            'testing',
            'raw_image_uploader',
            'replication',
            'publisher',
            'deprecation'
        ]
    }
    mock_get_current_obj.return_value = app

    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_accounts': [{'name': 'acnt1', 'data': 'more_stuff'}],
        'cloud_groups': ['group1'],
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    result = validate_ec2_job(job_doc)

    assert 'target_account_info' in result
    assert 'cloud_accounts' not in result
    assert 'cloud_groups' not in result

    # Test doc with no accounts
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_groups': ['group1'],
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    validate_ec2_job(job_doc)

    # Test doc with no groups
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_accounts': [{'name': 'acnt1', 'data': 'more_stuff'}],
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    validate_ec2_job(job_doc)

    # Test doc using cloud_account
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image'
    }

    result = validate_ec2_job(job_doc)
    assert 'cloud_account' not in result

    # Test doc with valid image tags
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'image_tags': [{"Key": "key", "Value": "value"}]
    }

    result = validate_ec2_job(job_doc)

    # Test doc with TPM and no uefi
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_groups': ['group1'],
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'tpm_support': 'v2.0'
    }
    with raises(MashJobException):
        validate_ec2_job(job_doc)

    # The create service only uses the first boot firmware
    job_doc['boot_firmware'] = ['uefi-preferred', 'uefi']
    with raises(MashJobException):
        validate_ec2_job(job_doc)

    job_doc['boot_firmware'] = ['uefi', 'uefi-preferred']
    validate_ec2_job(job_doc)

    # Root swap settings are kept and passed on
    mock_add_target_account.reset_mock()
    job_doc = {
        'last_service': 'testing',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'use_root_swap': True,
        'launch_inst_type': 'm1.large'
    }
    result = validate_ec2_job(job_doc)
    assert result['use_root_swap'] is True
    assert result['launch_inst_type'] == 'm1.large'
    assert mock_add_target_account.call_args[0][3] is True


@patch.object(LocalProxy, '_get_current_object')
def test_validate_mp_fields(mock_get_current_obj):
    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'download',
            'upload',
            'create',
            'test',
            'raw_image_upload',
            'replicate',
            'publish',
            'deprecate'
        ]
    }
    mock_get_current_obj.return_value = app

    job_doc = {
        'last_service': 'publish',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'publish_in_marketplace': True
    }

    with raises(MashJobException):
        validate_ec2_job(job_doc)
