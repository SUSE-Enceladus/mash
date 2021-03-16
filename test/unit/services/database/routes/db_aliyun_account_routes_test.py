import json

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, Mock

from sqlalchemy.orm.exc import NoResultFound


@patch('mash.services.database.utils.accounts.aliyun.handle_request')
@patch('mash.services.database.utils.accounts.aliyun.db')
def test_add_account_aliyun(
    mock_db,
    mock_handle_request,
    test_client
):
    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'access_key': 'string',
            'access_secret': 'string'
        },
        'bucket': 'bucket1',
        'region': 'cn-beijing',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1',
    }

    response = test_client.post(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['name'] == 'test'
    assert response.json['region'] == 'cn-beijing'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create Aliyun account: Broken"}\n'

    # Integrity Error
    mock_db.session.commit.side_effect = IntegrityError('Broken', None, None)

    response = test_client.post(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Account already exists"}\n'


@patch('mash.services.database.utils.accounts.aliyun.get_aliyun_account_for_user')
@patch('mash.services.database.utils.accounts.aliyun.handle_request')
@patch('mash.services.database.utils.accounts.aliyun.db')
def test_delete_account_aliyun(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'cn-beijing'
    account.security_group_id = 'sg1'
    account.vswitch_id = 'vs1'

    mock_get_account.return_value = account
    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.delete(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":1}\n'

    # Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 400
    assert response.data == b'{"msg":"Delete Aliyun account failed"}\n'

    # Not found
    mock_get_account.return_value = None

    response = test_client.delete(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"rows_deleted":0}\n'


@patch('mash.services.database.utils.accounts.aliyun.handle_request')
@patch('mash.services.database.utils.accounts.aliyun.AliyunAccount')
def test_get_account_aliyun(
    mock_aliyun_account,
    mock_handle_request,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'cn-beijing'
    account.security_group_id = 'sg1'
    account.vswitch_id = 'vs1'

    queryset = Mock()
    queryset.one.return_value = account
    mock_aliyun_account.query.filter_by.return_value = queryset

    request = {'name': 'test', 'user_id': 'user1'}

    response = test_client.get(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['id'] == '1'
    assert response.json['name'] == 'user1'
    assert response.json['region'] == 'cn-beijing'
    assert response.json['security_group_id'] == 'sg1'
    assert response.json['vswitch_id'] == 'vs1'

    # Not found
    mock_aliyun_account.query.filter_by.side_effect = NoResultFound()

    response = test_client.get(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'


@patch('mash.services.database.utils.accounts.aliyun.get_user_by_id')
def test_get_account_list_aliyun(mock_get_user, test_client):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'cn-beijing'
    account.security_group_id = 'sg1'
    account.vswitch_id = 'vs1'

    user = Mock()
    user.aliyun_accounts = [account]
    mock_get_user.return_value = user

    response = test_client.get('/aliyun_accounts/list/user1')

    assert response.status_code == 200
    assert response.json[0]['id'] == '1'
    assert response.json[0]['name'] == 'user1'
    assert response.json[0]['region'] == 'cn-beijing'
    assert response.json[0]['security_group_id'] == 'sg1'
    assert response.json[0]['vswitch_id'] == 'vs1'


@patch('mash.services.database.utils.accounts.aliyun.get_aliyun_account_for_user')
@patch('mash.services.database.utils.accounts.aliyun.handle_request')
@patch('mash.services.database.utils.accounts.aliyun.db')
def test_update_account_aliyun(
    mock_db,
    mock_handle_request,
    mock_get_account,
    test_client
):
    account = Mock()
    account.id = '1'
    account.name = 'user1'
    account.bucket = 'images'
    account.region = 'cn-beijing'
    account.security_group_id = 'sg1'
    account.vswitch_id = 'vs1'

    mock_get_account.return_value = account

    request = {
        'user_id': 'user1',
        'account_name': 'test',
        'credentials': {
            'access_key': 'string',
            'access_secret': 'string'
        },
        'bucket': 'bucket1',
        'region': 'cn-beijing',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1',
    }

    response = test_client.put(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    assert response.status_code == 200

    # DB Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update Aliyun account failed"}\n'

    # Request exception
    mock_handle_request.side_effect = Exception('Broken')

    response = test_client.put(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Update Aliyun account failed"}\n'

    # Account not found
    mock_get_account.return_value = None

    response = test_client.put(
        '/aliyun_accounts/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{}\n'
