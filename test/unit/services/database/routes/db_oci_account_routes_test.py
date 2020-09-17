import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound


@patch('mash.services.database.utils.accounts.oci.get_fingerprint_from_private_key')
@patch('mash.services.database.utils.accounts.oci.handle_request')
@patch('mash.services.database.utils.accounts.oci.db')
def test_add_account_oci(
    mock_db,
    mock_handle_request,
    mock_get_fingerprint,
    test_client
):
    request = {
        'user_id': 'user1',
        'account_name': 'acnt1',
        'bucket': 'bucket1',
        'region': 'us-phoenix-1',
        'availability_domain': 'Omic:PHX-AD-1',
        'compartment_id': 'ocid1.compartment.oc1..',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..',
        'signing_key': 'signing_key'
    }
    mock_get_fingerprint.return_value = 'adcde12345'

    response = test_client.post(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['name'] == 'acnt1'
    assert response.json['region'] == 'us-phoenix-1'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create OCI account: Broken"}\n'

    # Integrity Error
    mock_db.session.commit.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Account already exists"}\n'


@patch('mash.services.database.utils.accounts.oci.get_oci_account_for_user')
@patch('mash.services.database.utils.accounts.oci.handle_request')
@patch('mash.services.database.utils.accounts.oci.db')
def test_delete_account_oci(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'

    mock_get_account.return_value = account
    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.delete(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete OCI account failed"}\n'

    # Not found
    mock_get_account.return_value = None

    response = test_client.delete(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.accounts.oci.handle_request')
@patch('mash.services.database.utils.accounts.oci.OCIAccount')
def test_get_account_oci(
    mock_oci_account,
    mock_handle_request,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'

    queryset = Mock()
    queryset.one.return_value = account
    mock_oci_account.query.filter_by.return_value = queryset

    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['region'] == "us-phoenix-1"

    # Not found
    mock_oci_account.query.filter_by.side_effect = NoResultFound()

    response = test_client.get(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'


@patch('mash.services.database.utils.accounts.oci.get_user_by_id')
def test_get_account_list_oci(mock_get_user, test_client):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'

    user = Mock()
    user.oci_accounts = [account]
    mock_get_user.return_value = user

    response = test_client.get('/oci_accounts/list/user1')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['region'] == "us-phoenix-1"


@patch('mash.services.database.utils.accounts.oci.get_fingerprint_from_private_key')
@patch('mash.services.database.utils.accounts.oci.get_oci_account_for_user')
@patch('mash.services.database.utils.accounts.oci.handle_request')
@patch('mash.services.database.utils.accounts.oci.db')
def test_update_account_oci(
    mock_db,
    mock_handle_request,
    mock_get_account,
    mock_get_fingerprint,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-phoenix-1'

    mock_get_account.return_value = account

    request = {
        'user_id': 'user1',
        'account_name': 'acnt1',
        'bucket': 'bucket1',
        'region': 'us-phoenix-1',
        'availability_domain': 'Omic:PHX-AD-1',
        'compartment_id': 'ocid1.compartment.oc1..',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..',
        'signing_key': 'signing_key'
    }
    mock_get_fingerprint.return_value = 'adcde12345'

    response = test_client.put(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200

    # DB Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update OCI account failed"}\n'

    # Request exception
    mock_handle_request.side_effect = Exception('Broken')

    response = test_client.put(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update OCI account failed"}\n'

    # Account not found
    mock_get_account.return_value = None

    response = test_client.put(
        '/oci_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'
