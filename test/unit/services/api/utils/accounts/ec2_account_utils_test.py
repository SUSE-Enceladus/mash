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

from mash.mash_exceptions import MashDBException
from mash.services.api.models import EC2Account
from mash.services.api.utils.accounts.ec2 import (
    get_ec2_group,
    create_ec2_region,
    create_ec2_account,
    get_ec2_accounts,
    get_ec2_account,
    delete_ec2_account,
    update_ec2_account
)

from werkzeug.local import LocalProxy


@patch('mash.services.api.utils.accounts.ec2.EC2Group')
def test_get_ec2_group(mock_ec2_group):
    group = Mock()
    queryset = Mock()
    queryset.first.return_value = group
    mock_ec2_group.query.filter_by.return_value = queryset

    assert get_ec2_group('group1', 1) == group

    queryset.first.return_value = None

    with raises(MashDBException):
        get_ec2_group('group2', 1)


@patch('mash.services.api.utils.accounts.ec2.db')
def test_create_ec2_region(mock_db):
    account = EC2Account(
        name='acnt1',
        partition='aws',
        region='us-east-99',
        user_id=1
    )
    result = create_ec2_region('us-east-99', 'ami-987654', account)

    assert result.name == 'us-east-99'
    assert result.helper_image == 'ami-987654'

    mock_db.session.add.assert_called_once_with(result)


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.ec2.EC2Account')
@patch('mash.services.api.utils.accounts.ec2.EC2Group')
@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.utils.accounts.ec2.create_ec2_region')
@patch('mash.services.api.utils.accounts.ec2.get_user_by_id')
@patch('mash.services.api.utils.accounts.ec2.db')
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

    result = create_ec2_account(
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

    mock_db.session.add.has_calls([
        call(group),
        call(account)
    ])
    mock_db.session.commit.assert_called_once_with()

    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        create_ec2_account(
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


@patch('mash.services.api.utils.accounts.ec2.get_user_by_id')
def test_get_ec2_accounts(mock_get_user):
    account = Mock()
    user = Mock()
    user.ec2_accounts = [account]
    mock_get_user.return_value = user

    assert get_ec2_accounts(1) == [account]


@patch('mash.services.api.utils.accounts.ec2.EC2Account')
def test_get_ec2_account(mock_ec2_account):
    account = Mock()
    queryset = Mock()
    queryset.one.return_value = account
    mock_ec2_account.query.filter_by.return_value = queryset

    assert get_ec2_account('acnt1', 1) == account

    mock_ec2_account.query.filter_by.side_effect = Exception('Broken')

    with raises(MashDBException):
        get_ec2_account('acnt1', 2)


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.utils.accounts.ec2.get_ec2_account')
@patch('mash.services.api.utils.accounts.ec2.db')
def test_delete_ec2_account(
    mock_db,
    mock_get_account,
    mock_handle_request,
    mock_get_current_object
):
    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    account = Mock()
    mock_get_account.return_value = account

    data = {
        'cloud': 'ec2',
        'account_name': 'acnt1',
        'requesting_user': 1
    }

    assert delete_ec2_account('acnt1', 1) == 1

    mock_db.session.delete.assert_called_once_with(account)
    mock_db.session.commit.assert_called_once_with()
    mock_handle_request.assert_called_once_with(
        'http://localhost:5000/',
        'credentials/',
        'delete',
        job_data=data
    )

    mock_db.session.commit.side_effect = Exception('Broken')

    with raises(Exception):
        delete_ec2_account('acnt1', 1)

    mock_db.session.rollback.assert_called_once_with()

    mock_get_account.return_value = None
    assert delete_ec2_account('acnt2', 1) == 0


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.ec2.get_ec2_account')
@patch('mash.services.api.utils.accounts.ec2._get_or_create_ec2_group')
@patch('mash.services.api.utils.accounts.ec2.handle_request')
@patch('mash.services.api.utils.accounts.ec2.create_ec2_region')
@patch('mash.services.api.utils.accounts.ec2.get_user_by_id')
@patch('mash.services.api.utils.accounts.ec2.db')
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

    result = update_ec2_account(
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

    # Account not found
    mock_get_ec2_account.return_value = None

    result = update_ec2_account(
        'acnt1',
        1,
        [{'name': 'us-east-100', 'helper_image': 'ami-789'}],
        credentials,
        'group1',
        'us-east-99',
        'subnet-12345'
    )

    assert result is None

    # DB exception
    mock_get_ec2_account.return_value = account
    mock_db.session.commit.side_effect = Exception('Broken')

    with raises(Exception):
        update_ec2_account(
            'acnt1',
            1,
            [{'name': 'us-east-100', 'helper_image': 'ami-789'}],
            credentials,
            'group1',
            'us-east-99',
            'subnet-12345'
        )

    mock_db.session.rollback.assert_called_once_with()

    # Credentials update exception
    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        update_ec2_account(
            'acnt1',
            1,
            [{'name': 'us-east-100', 'helper_image': 'ami-789'}],
            credentials,
            'group1',
            'us-east-99',
            'subnet-12345'
        )
