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
from mash.services.api.utils.accounts.oci import (
    create_oci_account,
    get_oci_accounts,
    get_oci_account,
    delete_oci_account,
    update_oci_account
)


@patch('mash.services.api.utils.accounts.oci.get_fingerprint_from_private_key')
@patch('mash.services.api.utils.accounts.oci.current_app')
@patch('mash.services.api.utils.accounts.oci.OCIAccount')
@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.utils.accounts.oci.get_user_by_id')
@patch('mash.services.api.utils.accounts.oci.db')
def test_create_oci_account(
    mock_db,
    mock_get_user,
    mock_handle_request,
    mock_oci_account,
    mock_current_app,
    mock_fingerprint
):
    user = Mock()
    user.id = 1
    mock_get_user.return_value = user

    account = Mock()
    mock_oci_account.return_value = account

    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}
    mock_fingerprint.return_value = 'fingerprint'

    credentials = {
        'signing_key': 'signing key',
        'fingerprint': 'fingerprint'
    }
    data = {
        'cloud': 'oci',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = create_oci_account(
        1,
        'acnt1',
        'images',
        'us-phoenix-1',
        'Omic:PHX-AD-1',
        'ocid1.compartment.oc1..',
        'ocid1.user.oc1..',
        'ocid1.tenancy.oc1..',
        'signing key'
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
        create_oci_account(
            1,
            'acnt1',
            'images',
            'us-phoenix-1',
            'Omic:PHX-AD-1',
            'ocid1.compartment.oc1..',
            'ocid1.user.oc1..',
            'ocid1.tenancy.oc1..',
            'signing key'
        )

    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.utils.accounts.oci.get_user_by_id')
def test_get_oci_accounts(mock_get_user):
    account = Mock()
    user = Mock()
    user.oci_accounts = [account]
    mock_get_user.return_value = user

    assert get_oci_accounts('user1') == [account]


@patch('mash.services.api.utils.accounts.oci.OCIAccount')
def test_get_oci_account(mock_oci_account):
    account = Mock()
    queryset = Mock()
    queryset.one.return_value = account
    mock_oci_account.query.filter_by.return_value = queryset

    assert get_oci_account('acnt1', 1) == account

    mock_oci_account.query.filter_by.side_effect = Exception('Broken')

    with raises(MashDBException):
        get_oci_account('acnt1', 2)


@patch('mash.services.api.utils.accounts.oci.current_app')
@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.utils.accounts.oci.get_oci_account')
@patch('mash.services.api.utils.accounts.oci.db')
def test_delete_oci_account(
    mock_db,
    mock_get_account,
    mock_handle_request,
    mock_current_app
):
    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}

    account = Mock()
    mock_get_account.return_value = account

    data = {
        'cloud': 'oci',
        'account_name': 'acnt1',
        'requesting_user': 1
    }

    assert delete_oci_account('acnt1', 1) == 1

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
        delete_oci_account('acnt1', 1)

    mock_db.session.rollback.assert_called_once_with()

    mock_get_account.return_value = None
    assert delete_oci_account('acnt2', 1) == 0


@patch('mash.services.api.utils.accounts.oci.get_fingerprint_from_private_key')
@patch('mash.services.api.utils.accounts.oci.current_app')
@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.utils.accounts.oci.get_oci_account')
@patch('mash.services.api.utils.accounts.oci.db')
def test_update_oci_account(
    mock_db,
    mock_get_oci_account,
    mock_handle_request,
    mock_current_app,
    mock_fingerprint
):
    account = Mock()
    account.id = 1
    account.is_publishing_account = True
    mock_get_oci_account.return_value = account

    mock_current_app.config = {'CREDENTIALS_URL': 'http://localhost:5000/'}
    mock_fingerprint.return_value = 'fingerprint'

    credentials = {
        'signing_key': 'signing key',
        'fingerprint': 'fingerprint'
    }
    data = {
        'cloud': 'oci',
        'account_name': 'acnt1',
        'requesting_user': 1,
        'credentials': credentials
    }

    result = update_oci_account(
        1,
        'acnt1',
        bucket='images',
        region='us-phoenix-1',
        availability_domain='Omic:PHX-AD-1',
        compartment_id='ocid1.compartment.oc1..',
        oci_user_id='ocid1.user.oc1..',
        tenancy='ocid1.tenancy.oc1..',
        signing_key='signing key'
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
        update_oci_account(
            'user1',
            'acnt1',
            bucket='images',
        )

    mock_db.session.rollback.assert_called_once_with()

    # Exception in handle request
    mock_handle_request.side_effect = Exception('Broken')

    with raises(Exception):
        update_oci_account(
            1,
            'acnt1',
            signing_key='signing key',
        )

    # Account not found
    mock_get_oci_account.return_value = None

    result = update_oci_account(
        1,
        'acnt1',
        bucket='images',
    )

    assert result is None
