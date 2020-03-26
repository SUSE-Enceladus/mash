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
from mash.services.api.utils.accounts.azure import (
    create_azure_account,
    get_azure_accounts,
    get_azure_account,
    delete_azure_account,
    update_azure_account
)

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.azure.AzureAccount')
@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.utils.accounts.azure.db')
def test_create_azure_account(
    mock_db,
    mock_handle_request,
    mock_azure_account,
    mock_get_current_object
):
    account = Mock()
    mock_azure_account.return_value = account

    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'azure',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = create_azure_account(
        1,
        'acnt1',
        'useast',
        credentials,
        'container1',
        'group1',
        'account1',
        'container2',
        'group2',
        'account2'
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
        create_azure_account(
            1,
            'acnt1',
            'useast',
            credentials,
            'container1',
            'group1',
            'account1',
            'container2',
            'group2',
            'account2'
        )

    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.utils.accounts.azure.get_user_by_id')
def test_get_azure_accounts(mock_get_user):
    account = Mock()
    user = Mock()
    user.azure_accounts = [account]
    mock_get_user.return_value = user

    assert get_azure_accounts(1) == [account]


@patch('mash.services.api.utils.accounts.azure.AzureAccount')
def test_get_azure_account(mock_azure_account):
    account = Mock()
    queryset = Mock()
    queryset.one.return_value = account
    mock_azure_account.query.filter_by.return_value = queryset

    assert get_azure_account('acnt1', 1) == account

    mock_azure_account.query.filter_by.side_effect = Exception('Broken')

    with raises(MashDBException):
        get_azure_account('acnt1', 2)


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.utils.accounts.azure.get_azure_account')
@patch('mash.services.api.utils.accounts.azure.db')
def test_delete_azure_account(
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
        'cloud': 'azure',
        'account_name': 'acnt1',
        'requesting_user': 1
    }

    assert delete_azure_account('acnt1', 1) == 1

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
        delete_azure_account('acnt1', 1)

    mock_db.session.rollback.assert_called_once_with()

    mock_get_account.return_value = None
    assert delete_azure_account('acnt2', 1) == 0


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.accounts.azure.handle_request')
@patch('mash.services.api.utils.accounts.azure.get_azure_account')
@patch('mash.services.api.utils.accounts.azure.db')
def test_update_azure_account(
    mock_db,
    mock_get_azure_account,
    mock_handle_request,
    mock_get_current_object
):
    account = Mock()
    account.id = 1
    mock_get_azure_account.return_value = account

    app = Mock()
    mock_get_current_object.return_value = app
    app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'azure',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = update_azure_account(
        'acnt1',
        1,
        region='westus',
        credentials=credentials,
        source_container='container1',
        source_resource_group='group1',
        source_storage_account='account1',
        destination_container='container2',
        destination_resource_group='group2',
        destination_storage_account='account2'
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
        update_azure_account(
            'acnt1',
            1,
            region='westus'
        )

    mock_db.session.rollback.assert_called_once_with()

    # Exception in handle request
    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        update_azure_account(
            'acnt1',
            1,
            region='westus',
            credentials=credentials
        )

    # Account not found
    mock_get_azure_account.return_value = None

    result = update_azure_account(
        'acnt1',
        1,
        region='westus',
    )

    assert result is None
