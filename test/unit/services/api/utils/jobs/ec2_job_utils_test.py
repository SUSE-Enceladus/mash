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
from mash.services.api.utils.jobs.ec2 import (
    get_ec2_regions_by_partition,
    get_ec2_helper_images,
    add_target_ec2_account,
    convert_account_dict,
    update_ec2_job_accounts
)


@patch('mash.services.api.utils.jobs.ec2.current_app')
def test_get_ec2_regions_by_partition(mock_current_app):
    mock_current_app.config = {
        'CLOUD_DATA': {
            'ec2': {
                'regions': {
                    'aws': ['us-east-99']
                }
            }
        }
    }

    assert get_ec2_regions_by_partition('aws') == ['us-east-99']


@patch('mash.services.api.utils.jobs.ec2.current_app')
def test_get_ec2_helper_images(mock_current_app):
    mock_current_app.config = {
        'CLOUD_DATA': {
            'ec2': {
                'helper_images': {
                    'us-east-99': 'ami-789'
                }
            }
        }
    }

    images = get_ec2_helper_images()
    assert images['us-east-99'] == 'ami-789'


@patch('mash.services.api.utils.jobs.ec2.get_ec2_regions_by_partition')
def test_add_target_ec2_account(mock_get_regions):
    account = Mock()
    account.region = 'us-east-100'
    account.name = 'acnt1'

    region = Mock()
    region.name = 'us-east-100'
    region.helper_image = 'ami-987'

    account.additional_regions = [region]
    mock_get_regions.return_value = ['us-east-99']

    cloud_accounts = {'acnt1': {'root_swap_ami': 'ami-456'}}
    accounts = {}
    helper_images = {'us-east-99': 'ami-789'}

    add_target_ec2_account(
        account,
        accounts,
        cloud_accounts,
        helper_images,
        use_root_swap=True
    )

    assert 'us-east-100' in accounts
    assert accounts['us-east-100']['account'] == 'acnt1'
    assert accounts['us-east-100']['helper_image'] == 'ami-456'
    assert 'us-east-99' in accounts['us-east-100']['target_regions']
    assert 'us-east-100' in accounts['us-east-100']['target_regions']

    cloud_accounts = {'acnt1': {}}

    with raises(MashJobException):
        add_target_ec2_account(
            account,
            accounts,
            cloud_accounts,
            helper_images,
            use_root_swap=True
        )

    add_target_ec2_account(
        account,
        accounts,
        cloud_accounts,
        helper_images
    )

    assert accounts['us-east-100']['helper_image'] == 'ami-987'


def test_convert_account_dict():
    accounts = [{'name': 'acnt1', 'data': 'more_stuff'}]
    assert convert_account_dict(accounts)['acnt1']['data'] == 'more_stuff'


@patch('mash.services.api.utils.jobs.ec2.add_target_ec2_account')
@patch('mash.services.api.utils.jobs.ec2.get_ec2_account_by_id')
@patch('mash.services.api.utils.jobs.ec2.get_ec2_group')
@patch('mash.services.api.utils.jobs.ec2.get_ec2_helper_images')
@patch('mash.services.api.utils.jobs.ec2.get_user_by_username')
def test_update_ec2_job_accounts(
    mock_get_user,
    mock_get_helper_images,
    mock_get_group,
    mock_get_ec2_account,
    mock_add_target_account
):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    account = Mock()
    account.name = 'acnt1'
    mock_get_ec2_account.return_value = account

    group = Mock()
    group.accounts = [account]
    mock_get_group.return_value = group

    mock_get_helper_images.return_value = {'us-east-99': 'ami-789'}

    job_doc = {
        'requesting_user': 'user1',
        'cloud_accounts': [{'name': 'acnt1', 'data': 'more_stuff'}],
        'cloud_groups': ['group1']
    }

    result = update_ec2_job_accounts(job_doc)

    assert 'target_account_info' in result
    assert 'cloud_accounts' not in result
    assert 'cloud_groups' not in result

    # Test doc with no accounts
    job_doc = {
        'requesting_user': 'user1',
        'cloud_groups': ['group1']
    }

    update_ec2_job_accounts(job_doc)

    # Test doc with no groups
    job_doc = {
        'requesting_user': 'user1',
        'cloud_accounts': [{'name': 'acnt1', 'data': 'more_stuff'}]
    }

    update_ec2_job_accounts(job_doc)

    # Test doc using cloud_account
    job_doc = {
        'requesting_user': 'user1',
        'cloud_account': 'acnt1'
    }

    result = update_ec2_job_accounts(job_doc)

    assert 'cloud_account' not in result
