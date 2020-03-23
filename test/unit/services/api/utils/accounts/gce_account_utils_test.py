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

from mash.mash_exceptions import MashDBException
from mash.services.api.utils.accounts.gce import (
    create_gce_account,
    get_gce_accounts,
    get_gce_account,
    delete_gce_account,
    update_gce_account
)


@patch('mash.services.api.utils.accounts.gce.current_app')
@patch('mash.services.api.utils.accounts.gce.GCEAccount')
@patch('mash.services.api.utils.accounts.gce.handle_request')
@patch('mash.services.api.utils.accounts.gce.db')
def test_create_gce_account(
    mock_db,
    mock_handle_request,
    mock_gce_account,
    mock_current_app
):
    account = Mock()
    mock_gce_account.return_value = account

    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'gce',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = create_gce_account(
        1,
        'acnt1',
        'images',
        'us-east1',
        credentials,
        None,
        False
    )

    assert result == account

    mock_handle_request.assert_called_once_with(
        'http://localhost:5000/',
        'credentials/',
        'post',
        job_data=data
    )

    mock_db.session.add.assert_called_once_with(account)
    mock_db.session.commit.assert_called_once_with()

    # Exception

    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        create_gce_account(
            1,
            'acnt1',
            'images',
            'us-east1',
            credentials,
            None,
            False
        )

    mock_db.session.rollback.assert_called_once_with()

    # Publishing account with no testing account

    with raises(MashDBException):
        create_gce_account(
            1,
            'acnt1',
            'images',
            'us-east1',
            credentials,
            None,
            True
        )


@patch('mash.services.api.utils.accounts.gce.get_user_by_id')
def test_get_gce_accounts(mock_get_user):
    account = Mock()
    user = Mock()
    user.gce_accounts = [account]
    mock_get_user.return_value = user

    assert get_gce_accounts(1) == [account]


@patch('mash.services.api.utils.accounts.gce.GCEAccount')
def test_get_gce_account(mock_gce_account):
    account = Mock()
    queryset = Mock()
    queryset.one.return_value = account
    mock_gce_account.query.filter_by.return_value = queryset

    assert get_gce_account('acnt1', 1) == account

    mock_gce_account.query.filter_by.side_effect = Exception('Broken')

    with raises(MashDBException):
        get_gce_account('acnt1', 2)


@patch('mash.services.api.utils.accounts.gce.current_app')
@patch('mash.services.api.utils.accounts.gce.handle_request')
@patch('mash.services.api.utils.accounts.gce.get_gce_account')
@patch('mash.services.api.utils.accounts.gce.db')
def test_delete_gce_account(
    mock_db,
    mock_get_account,
    mock_handle_request,
    mock_current_app
):
    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    account = Mock()
    mock_get_account.return_value = account

    data = {
        'cloud': 'gce',
        'account_name': 'acnt1',
        'requesting_user': 1
    }

    assert delete_gce_account('acnt1', 1) == 1

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
        delete_gce_account('acnt1', 1)

    mock_db.session.rollback.assert_called_once_with()

    mock_get_account.return_value = None
    assert delete_gce_account('acnt2', 1) == 0


@patch('mash.services.api.utils.accounts.gce.current_app')
@patch('mash.services.api.utils.accounts.gce.handle_request')
@patch('mash.services.api.utils.accounts.gce.get_gce_account')
@patch('mash.services.api.utils.accounts.gce.db')
def test_update_gce_account(
    mock_db,
    mock_get_gce_account,
    mock_handle_request,
    mock_current_app
):
    account = Mock()
    account.id = 1
    account.is_publishing_account = True
    mock_get_gce_account.return_value = account

    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'gce',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = update_gce_account(
        'acnt1',
        1,
        bucket='images',
        region='us-east1',
        credentials=credentials,
        testing_account='tester'
    )

    assert result == account

    mock_handle_request.assert_called_once_with(
        'http://localhost:5000/',
        'credentials/',
        'post',
        job_data=data
    )

    mock_db.session.add.assert_called_once_with(account)
    mock_db.session.commit.assert_called_once_with()

    # Exception in database
    mock_db.session.commit.side_effect = Exception('Broken')

    with raises(Exception):
        update_gce_account(
            'acnt1',
            1,
            bucket='images',
            region='us-east1',
            credentials=credentials,
            testing_account='tester'
        )

    mock_db.session.rollback.assert_called_once_with()

    # Exception in handle request
    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        update_gce_account(
            'acnt1',
            1,
            bucket='images',
            region='us-east1',
            credentials=credentials,
            testing_account='tester'
        )

    # Account not found
    mock_get_gce_account.return_value = None

    result = update_gce_account(
        'acnt1',
        1,
        bucket='images',
        region='us-east1',
        credentials=credentials,
        testing_account='tester'
    )

    assert result is None
