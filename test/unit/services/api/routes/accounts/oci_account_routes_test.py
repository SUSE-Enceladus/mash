import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.routes.accounts.oci.create_oci_account')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_create_oci_account,
        test_client
):
    mock_jwt_identity.return_value = 'user1'
    request = {
        'account_name': 'acnt1',
        'bucket': 'bucket1',
        'region': 'us-phoenix-1',
        'availability_domain': 'Omic:PHX-AD-1',
        'compartment_id': 'ocid1.compartment.oc1..',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..',
        'signing_key': 'signing_key'
    }
    response = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_create_oci_account.assert_called_once_with(
        'user1',
        'acnt1',
        'bucket1',
        'us-phoenix-1',
        'Omic:PHX-AD-1',
        'ocid1.compartment.oc1..',
        'ocid1.user.oc1..',
        'ocid1.tenancy.oc1..',
        'signing_key'
    )

    assert response.status_code == 201

    # Mash Exception
    mock_create_oci_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Integrity Error
    mock_create_oci_account.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 409
    assert response.data == b'{"msg":"Account already exists"}\n'

    # Exception
    mock_create_oci_account.side_effect = Exception('Broken')

    response = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to add OCI account"}\n'


@patch('mash.services.api.routes.accounts.oci.delete_oci_account')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_oci_account,
        test_client
):
    mock_delete_oci_account.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete('/accounts/oci/test')

    assert response.status_code == 200
    assert response.data == b'{"msg":"OCI account deleted"}\n'

    # Not found
    mock_delete_oci_account.return_value = 0

    response = test_client.delete('/accounts/oci/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"OCI account not found"}\n'

    # Exception
    mock_delete_oci_account.side_effect = Exception('Broken')

    response = test_client.delete('/accounts/oci/test')
    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete OCI account failed"}\n'


@patch('mash.services.api.routes.accounts.oci.get_oci_account')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_oci_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'
    account.testing_account = None
    account.is_publishing_account = False

    mock_get_oci_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/oci/test')

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['bucket'] == "images"
    assert response.json['region'] == "us-phoenix-1"

    # Not found
    mock_get_oci_account.return_value = None

    response = test_client.get('/accounts/oci/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"OCI account not found"}\n'


@patch('mash.services.api.routes.accounts.oci.get_oci_accounts')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_oci_accounts,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'
    account.testing_account = None
    account.is_publishing_account = False

    mock_get_oci_accounts.return_value = [account]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/accounts/oci/')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['bucket'] == "images"
    assert response.json[0]['region'] == "us-phoenix-1"


@patch('mash.services.api.routes.accounts.oci.update_oci_account')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_update_oci_account,
        test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'
    account.testing_account = None
    account.is_publishing_account = False

    mock_update_oci_account.return_value = account
    mock_jwt_identity.return_value = 'user1'

    request = {
        'bucket': 'bucket1',
        'region': 'us-phoenix-1'
    }

    response = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_update_oci_account.assert_called_once_with(
        'user1',
        'acnt1',
        'bucket1',
        'us-phoenix-1',
        None,
        None,
        None,
        None,
        None
    )

    assert response.status_code == 200

    # Mash Exception
    mock_update_oci_account.side_effect = MashException('Broken')

    response = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'

    # Account not found
    mock_update_oci_account.side_effect = None
    mock_update_oci_account.return_value = None

    response = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"OCI account not found"}\n'
