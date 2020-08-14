import json

from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException


@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_account_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
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
    response = Mock()
    response.json.return_value = request
    mock_handle_request.return_value = response

    result = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 201

    # Exception
    mock_handle_request.side_effect = Exception('Failed to add OCI account')

    result = test_client.post(
        '/accounts/oci/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Failed to add OCI account"}\n'


@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_account_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    response = Mock()
    response.json.return_value = {'rows_deleted': 1}
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.delete('/accounts/oci/test')

    assert result.status_code == 200
    assert result.data == b'{"msg":"OCI account deleted"}\n'

    # Not found
    response.json.return_value = {'rows_deleted': 0}

    result = test_client.delete('/accounts/oci/test')
    assert result.status_code == 404
    assert result.data == b'{"msg":"OCI account not found"}\n'

    # Exception
    mock_handle_request.side_effect = Exception('Broken')

    result = test_client.delete('/accounts/oci/test')
    assert result.status_code == 400
    assert result.data == b'{"msg":"Delete OCI account failed"}\n'


@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-phoenix-1'
    }

    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/oci/test')

    assert result.status_code == 200
    assert result.json['id'] == "1"
    assert result.json['name'] == "user1"
    assert result.json['bucket'] == "images"
    assert result.json['region'] == "us-phoenix-1"

    # Not found
    response.json.return_value = {}

    response = test_client.get('/accounts/oci/test')
    assert response.status_code == 404
    assert response.data == b'{"msg":"OCI account not found"}\n'


@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_account_list_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-phoenix-1'
    }

    response = Mock()
    response.json.return_value = [account]
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    result = test_client.get('/accounts/oci/')

    assert result.status_code == 200
    assert result.json[0]['id'] == "1"
    assert result.json[0]['name'] == "user1"
    assert result.json[0]['bucket'] == "images"
    assert result.json[0]['region'] == "us-phoenix-1"


@patch('mash.services.api.utils.accounts.oci.handle_request')
@patch('mash.services.api.routes.accounts.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_update_account_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_handle_request,
    test_client
):
    account = {
        'id': '1',
        'name': 'user1',
        'bucket': 'images',
        'region': 'us-phoenix-1'
    }

    response = Mock()
    response.json.return_value = account
    mock_handle_request.return_value = response
    mock_jwt_identity.return_value = 'user1'

    request = {
        'bucket': 'bucket1',
        'region': 'us-phoenix-1'
    }

    result = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert result.status_code == 200

    # Account not found
    response.json.return_value = {}

    result = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"OCI account not found"}\n'

    # Mash Exception
    mock_handle_request.side_effect = MashException('Broken')

    result = test_client.post(
        '/accounts/oci/acnt1',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert result.status_code == 400
    assert result.data == b'{"msg":"Broken"}\n'
