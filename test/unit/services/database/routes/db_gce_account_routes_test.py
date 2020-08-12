import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound


@patch('mash.services.database.utils.accounts.gce.handle_request')
@patch('mash.services.database.utils.accounts.gce.db')
def test_add_account_gce(
    mock_db,
    mock_handle_request,
    test_client
):
    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'type': 'string',
            'project_id': 'string',
            'private_key_id': 'string',
            'private_key': 'string',
            'client_email': 'string',
            'client_id': 'string',
            'auth_uri': 'string',
            'token_uri': 'string',
            'auth_provider_x509_cert_url': 'string',
            'client_x509_cert_url': 'string'
        },
        'bucket': 'bucket1',
        'region': 'us-east-1'
    }

    response = test_client.post(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['name'] == 'test'
    assert response.json['region'] == 'us-east-1'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create GCE account: Broken"}\n'

    # Integrity Error
    mock_db.session.commit.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Account already exists"}\n'

    # No testing account
    request['is_publishing_account'] = True

    response = test_client.post(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    msg = b'{"msg":"Unable to create GCE account: ' \
          b'Jobs using a GCE publishing account require ' \
          b'the use of a test account."}\n'
    assert response.data == msg


@patch('mash.services.database.utils.accounts.gce.get_gce_account_for_user')
@patch('mash.services.database.utils.accounts.gce.handle_request')
@patch('mash.services.database.utils.accounts.gce.db')
def test_delete_account_gce(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.testing_account = None
    account.is_publishing_account = False

    mock_get_account.return_value = account
    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.delete(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete GCE account failed"}\n'

    # Not found
    mock_get_account.return_value = None

    response = test_client.delete(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.accounts.gce.handle_request')
@patch('mash.services.database.utils.accounts.gce.GCEAccount')
def test_get_account_gce(
    mock_gce_account,
    mock_handle_request,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.testing_account = None
    account.is_publishing_account = False

    queryset = Mock()
    queryset.one.return_value = account
    mock_gce_account.query.filter_by.return_value = queryset

    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['region'] == "us-east-1"

    # Not found
    mock_gce_account.query.filter_by.side_effect = NoResultFound()

    response = test_client.get(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'


@patch('mash.services.database.utils.accounts.gce.get_user_by_id')
def test_get_account_list_gce(mock_get_user, test_client):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.testing_account = None
    account.is_publishing_account = False

    user = Mock()
    user.gce_accounts = [account]
    mock_get_user.return_value = user

    response = test_client.get('/gce_accounts/list/user1')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['region'] == "us-east-1"


@patch('mash.services.database.utils.accounts.gce.get_gce_account_for_user')
@patch('mash.services.database.utils.accounts.gce.handle_request')
@patch('mash.services.database.utils.accounts.gce.db')
def test_update_account_gce(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'us-east-1'
    account.testing_account = 'fake'
    account.is_publishing_account = True

    mock_get_account.return_value = account

    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'type': 'string',
            'project_id': 'string',
            'private_key_id': 'string',
            'private_key': 'string',
            'client_email': 'string',
            'client_id': 'string',
            'auth_uri': 'string',
            'token_uri': 'string',
            'auth_provider_x509_cert_url': 'string',
            'client_x509_cert_url': 'string'
        },
        'bucket': 'bucket1',
        'region': 'us-east-1',
        'testing_account': 'new_acnt'
    }

    response = test_client.put(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200

    # DB Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update GCE account failed"}\n'

    # Request exception
    mock_handle_request.side_effect = Exception('Broken')

    response = test_client.put(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update GCE account failed"}\n'

    # Account not found
    mock_get_account.return_value = None

    response = test_client.put(
        '/gce_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'
