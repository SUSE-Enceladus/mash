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

from unittest.mock import patch, Mock, call

from pytest import raises

from mash.services.database.models import EC2Account
from mash.services.database.utils.accounts.ec2 import (
    create_new_ec2_region,
    create_new_ec2_account,
    update_ec2_account_for_user
)

from werkzeug.local import LocalProxy


@patch('mash.services.database.utils.accounts.ec2.db')
def test_create_ec2_region(mock_db):
    account = EC2Account(
        name='acnt1',
        partition='aws',
        region='us-east-99',
        user_id=1
    )
    result = create_new_ec2_region('us-east-99', 'ami-987654', account)

    assert result.name == 'us-east-99'
    assert result.helper_image == 'ami-987654'

    mock_db.session.add.assert_called_once_with(result)


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.database.utils.accounts.ec2.EC2Account')
@patch('mash.services.database.utils.accounts.ec2.EC2Group')
@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.create_new_ec2_region')
@patch('mash.services.database.utils.accounts.ec2.get_user_by_id')
@patch('mash.services.database.utils.accounts.ec2.db')
def test_create_ec2_account(
    mock_db,
    mock_get_user,
    mock_create_region,
    mock_handle_request,
    mock_ec2_group,
    mock_ec2_account,
    mock_get_current_object
):
    user = Mock()
    user.id = 1
    mock_get_user.return_value = user

    queryset = Mock()
    queryset.first.return_value = None
    mock_ec2_group.query.filter_by.return_value = queryset

    account = Mock()
    mock_ec2_account.return_value = account

    group = Mock()
    mock_ec2_group.return_value = group

    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'ec2',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = create_new_ec2_account(
        1,
        'acnt1',
        'aws',
        'us-east-99',
        credentials,
        'subnet-12345',
        'group1',
        [{'name': 'us-east-100', 'helper_image': 'ami-789'}]
    )

    assert result == account
    assert account.group == group

    mock_create_region.assert_called_once_with(
        'us-east-100', 'ami-789', account
    )

    mock_handle_request.assert_called_once_with(
        'http://localhost:5000/',
        'credentials/',
        'post',
        job_data=data
    )

    mock_db.session.add.assert_has_calls([
        call(group),
        call(account)
    ])
    mock_db.session.commit.assert_called_once_with()

    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        create_new_ec2_account(
            1,
            'acnt1',
            'aws',
            'us-east-99',
            credentials,
            'subnet-12345',
            'group1',
            [{'name': 'us-east-100', 'helper_image': 'ami-789'}]
        )

    mock_db.session.rollback.assert_called_once_with()


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.database.utils.accounts.ec2.get_ec2_account_for_user')
@patch('mash.services.database.utils.accounts.ec2._get_or_create_ec2_group')
@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.create_new_ec2_region')
@patch('mash.services.database.utils.accounts.ec2.get_user_by_id')
@patch('mash.services.database.utils.accounts.ec2.db')
def test_update_ec2_account(
    mock_db,
    mock_get_user,
    mock_create_region,
    mock_handle_request,
    mock_get_create_group,
    mock_get_ec2_account,
    mock_get_current_object
):
    user = Mock()
    user.id = 1
    mock_get_user.return_value = user

    group = Mock()
    group.id = 1
    mock_get_create_group.return_value = group

    account = Mock()
    mock_get_ec2_account.return_value = account

    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'ec2',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = update_ec2_account_for_user(
        'acnt1',
        1,
        [{'name': 'us-east-100', 'helper_image': 'ami-789'}],
        credentials,
        'group1',
        'us-east-99',
        'subnet-12345'
    )

    assert result == account
    assert account.group == group

    mock_create_region.assert_called_once_with(
        'us-east-100', 'ami-789', account
    )

    mock_handle_request.assert_called_once_with(
        'http://localhost:5000/',
        'credentials/',
        'post',
        job_data=data
    )

    mock_db.session.add.assert_called_once_with(account)
    mock_db.session.commit.assert_called_once_with()
