from pytest import raises

from unittest.mock import call, patch, Mock

from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashDBException

with patch('mash.services.base_config.BaseConfig') as mock_config:
    config = Mock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    config.get_credentials_url.return_value = 'http://localhost:8080/'
    mock_config.return_value = config

    from mash.services.api.models import EC2Account
    from mash.services.api.model_utils import (
        add_user,
        verify_login,
        get_user_by_username,
        get_user_email,
        delete_user,
        get_ec2_group,
        create_ec2_region,
        create_ec2_account,
        get_ec2_accounts,
        get_ec2_account,
        get_ec2_account_by_id,
        delete_ec2_account
    )


@patch('mash.services.api.model_utils.db')
def test_add_user(mock_db):
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user.username == 'user1'
    assert user.email == 'user1@fake.com'

    mock_db.session.commit.side_effect = IntegrityError(
        'Duplicate', None, None
    )
    user = add_user('user1', 'user1@fake.com', 'password123')

    assert user is None
    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.model_utils.get_user_by_username')
def test_verify_login(mock_get_user):
    user = Mock()
    user.check_password.side_effect = [True, False]
    mock_get_user.return_value = user

    assert verify_login('user1', 'password123') == user
    assert verify_login('user1', 'password321') is None


@patch('mash.services.api.model_utils.User')
def test_get_user_by_username(mock_user):
    user = Mock()
    queryset = Mock()
    queryset.first.return_value = user
    mock_user.query.filter_by.return_value = queryset

    assert get_user_by_username('user1') == user


@patch('mash.services.api.model_utils.get_user_by_username')
def test_get_user_email(mock_get_user):
    user = Mock()
    user.email = 'user1@fake.com'
    mock_get_user.return_value = user

    assert get_user_email('user1') == 'user1@fake.com'


@patch('mash.services.api.model_utils.db')
@patch('mash.services.api.model_utils.get_user_by_username')
def test_delete_user(mock_get_user, mock_db):
    user = Mock()
    mock_get_user.return_value = user

    assert delete_user('user1') == 1
    mock_db.session.delete.assert_called_once_with(user)

    mock_get_user.return_value = None
    assert delete_user('user1') == 0


@patch('mash.services.api.model_utils.EC2Group')
def test_get_ec2_group(mock_ec2_group):
    group = Mock()
    queryset = Mock()
    queryset.first.return_value = group
    mock_ec2_group.query.filter_by.return_value = queryset

    assert get_ec2_group('group1', '1') == group

    queryset.first.return_value = None

    with raises(MashDBException):
        get_ec2_group('group2', '1')


@patch('mash.services.api.model_utils.db')
def test_create_ec2_region(mock_db):
    account = EC2Account(
        name='acnt1',
        partition='aws',
        region='us-east-99',
        user_id='1'
    )
    result = create_ec2_region('us-east-99', 'ami-987654', account)

    assert result.name == 'us-east-99'
    assert result.helper_image == 'ami-987654'

    mock_db.session.add.assert_called_once_with(result)


@patch('mash.services.api.model_utils.EC2Account')
@patch('mash.services.api.model_utils.EC2Group')
@patch('mash.services.api.model_utils.handle_request')
@patch('mash.services.api.model_utils.create_ec2_region')
@patch('mash.services.api.model_utils.get_user_by_username')
@patch('mash.services.api.model_utils.db')
def test_create_ec2_account(
    mock_db,
    mock_get_user,
    mock_create_region,
    mock_handle_request,
    mock_ec2_group,
    mock_ec2_account
):
    user = Mock()
    user.id = '1'
    mock_get_user.return_value = user

    queryset = Mock()
    queryset.first.return_value = None
    mock_ec2_group.query.filter_by.return_value = queryset

    account = Mock()
    mock_ec2_account.return_value = account

    group = Mock()
    mock_ec2_group.return_value = group

    credentials = {'super': 'secret'}
    data = {
        'cloud': 'ec2',
        'account_name': 'acnt1',
        'requesting_user': 'user1',
        'credentials': credentials
    }

    result = create_ec2_account(
        'user1',
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
        'http://localhost:8080/',
        'credentials',
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
            'user1',
            'acnt1',
            'aws',
            'us-east-99',
            credentials,
            'subnet-12345',
            'group1',
            [{'name': 'us-east-100', 'helper_image': 'ami-789'}]
        )

    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.model_utils.get_user_by_username')
def test_get_ec2_accounts(mock_get_user):
    account = Mock()
    user = Mock()
    user.ec2_accounts = [account]
    mock_get_user.return_value = user

    assert get_ec2_accounts('user1') == [account]


@patch('mash.services.api.model_utils.EC2Account')
def test_get_ec2_account(mock_ec2_account):
    account = Mock()
    queryset = Mock()
    queryset2 = Mock()
    queryset2.first.return_value = account
    queryset.filter_by.return_value = queryset2
    mock_ec2_account.query.filter.return_value = queryset

    assert get_ec2_account('acnt1', 'user1') == account


@patch('mash.services.api.model_utils.EC2Account')
def test_get_ec2_account_by_id(mock_ec2_account):
    account = Mock()
    queryset = Mock()
    queryset.one.return_value = account
    mock_ec2_account.query.filter_by.return_value = queryset

    assert get_ec2_account_by_id('acnt1', '1') == account

    mock_ec2_account.query.filter_by.side_effect = Exception('Broken')

    with raises(MashDBException):
        get_ec2_account_by_id('acnt1', '2')


@patch('mash.services.api.model_utils.handle_request')
@patch('mash.services.api.model_utils.get_ec2_account')
@patch('mash.services.api.model_utils.db')
def test_delete_ec2_account(mock_db, mock_get_account, mock_handle_request):
    account = Mock()
    mock_get_account.return_value = account

    data = {
        'cloud': 'ec2',
        'account_name': 'acnt1',
        'requesting_user': 'user1'
    }

    assert delete_ec2_account('acnt1', 'user1') == 1

    mock_db.session.delete.assert_called_once_with(account)
    mock_db.session.commit.assert_called_once_with()
    mock_handle_request.assert_called_once_with(
        'http://localhost:8080/',
        'credentials',
        'delete',
        job_data=data
    )

    mock_db.session.commit.side_effect = Exception('Broken')

    with raises(Exception):
        delete_ec2_account('acnt1', 'user1')

    mock_db.session.rollback.assert_called_once_with()

    mock_get_account.return_value = None
    assert delete_ec2_account('acnt2', 'user1') == 0
