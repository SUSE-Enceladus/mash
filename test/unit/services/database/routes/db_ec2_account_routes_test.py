import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound


@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.db')
def test_add_account_ec2(
    mock_db,
    mock_handle_request,
    test_client
):
    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'partition': 'aws',
        'region': 'us-east-1'
    }

    response = test_client.post(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['name'] == 'test'
    assert response.json['region'] == 'us-east-1'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create EC2 account: Broken"}\n'

    # Integrity Error
    mock_db.session.commit.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Account already exists"}\n'


@patch('mash.services.database.utils.accounts.ec2.get_ec2_account_for_user')
@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.db')
def test_delete_account_ec2(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    mock_get_account.return_value = account
    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.delete(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete EC2 account failed"}\n'

    # Not found
    mock_get_account.return_value = None

    response = test_client.delete(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.EC2Account')
def test_get_account_ec2(
    mock_ec2_account,
    mock_handle_request,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    queryset = Mock()
    queryset.one.return_value = account
    mock_ec2_account.query.filter_by.return_value = queryset

    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == "1"
    assert response.json['name'] == "user1"
    assert response.json['region'] == "us-east-1"

    # Not found
    mock_ec2_account.query.filter_by.side_effect = NoResultFound()

    response = test_client.get(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'


@patch('mash.services.database.utils.accounts.ec2.get_user_by_id')
def test_get_account_list_ec2(mock_get_user, test_client):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    user = Mock()
    user.ec2_accounts = [account]
    mock_get_user.return_value = user

    response = test_client.get('/ec2_accounts/list/user1')

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['region'] == "us-east-1"


@patch('mash.services.database.utils.accounts.ec2.EC2Group')
def test_get_accounts_in_ec2_group(mock_group, test_client):
    group = Mock()
    queryset = Mock()
    queryset.one.return_value = group
    mock_group.query.filter_by.return_value = queryset

    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    group.accounts = [account]
    request = {'group_name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/ec2_accounts/group_accounts',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json[0]['id'] == "1"
    assert response.json[0]['name'] == "user1"
    assert response.json[0]['region'] == "us-east-1"

    # Not found
    queryset.one.side_effect = NoResultFound()

    response = test_client.get(
        '/ec2_accounts/group_accounts',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"Group test not found."}\n'


@patch('mash.services.database.utils.accounts.ec2._get_or_create_ec2_group')
@patch('mash.services.database.utils.accounts.ec2.get_ec2_account_for_user')
@patch('mash.services.database.utils.accounts.ec2.handle_request')
@patch('mash.services.database.utils.accounts.ec2.db')
def test_update_account_ec2(
    mock_db,
    mock_handle_request,
    mock_get_account,
    mock_get_group,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.partition = 'aws'
    account.region = 'us-east-1'
    account.subnet = None
    account.additional_regions = None
    account.group = None

    mock_get_account.return_value = account

    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'partition': 'aws',
        'region': 'us-east-1',
        'group': 'grp1',
        'subnet': 'subnet1'
    }

    response = test_client.put(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200

    # DB Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update EC2 account failed"}\n'

    # Request exception
    mock_handle_request.side_effect = Exception('Broken')

    response = test_client.put(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update EC2 account failed"}\n'

    # Account not found
    mock_get_account.return_value = None

    response = test_client.put(
        '/ec2_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'
