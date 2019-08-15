from unittest.mock import MagicMock, patch

with patch('mash.services.base_config.BaseConfig') as mock_config:
    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config
    from mash.services.api.models import (
        User,
        Token,
        EC2Account,
        EC2Group,
        EC2Region
    )


def test_user_model():
    user = User(
        username='user1',
        email='user1@fake.com'
    )
    user.set_password('password')
    assert user.check_password('password')
    assert user.__repr__() == '<User user1>'


def test_token_model():
    token = Token(
        jti='12345',
        token_type='access',
        user_id='1',
        expires=None
    )
    assert token.__repr__() == '<Token 12345>'


def test_ec2_account_model():
    account = EC2Account(
        name='acnt1',
        partition='aws',
        region='us-east-1',
        user_id='1'
    )
    assert account.__repr__() == '<EC2 Account acnt1>'


def test_ec2_group_model():
    group = EC2Group(
        name='group1',
        user_id='1'
    )
    assert group.__repr__() == '<EC2 Group group1>'


def test_ec2_region_model():
    region = EC2Region(
        name='us-east-99',
        helper_image='ami-1234567890',
        account_id='1'
    )
    assert region.__repr__() == '<EC2 Region us-east-99>'
