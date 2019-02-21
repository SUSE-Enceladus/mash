import json
import pytest

from unittest.mock import MagicMock, patch

from mash import wsgi


@pytest.fixture(scope='module')
def test_client():
    testing_client = wsgi.application.test_client()

    ctx = wsgi.application.app_context()
    ctx.push()

    yield testing_client
    ctx.pop()


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_add_account(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = json.dumps({
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'group': 'group1',
        'partition': 'aws',
        'cloud': 'ec2',
        'region': 'us-east-1',
        'requesting_user': 'user1'
    }, sort_keys=True)
    response = test_client.post(
        '/add_account',
        content_type='application/json',
        data=data
    )

    channel.basic.publish.assert_called_once_with(
        body=data,
        routing_key='add_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"status":"Add account request submitted."}\n'


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_add_account_error(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = json.dumps({
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'group': 'group1',
        'partition': 'aws',
        'cloud': 'fake',
        'requesting_user': 'user1'
    }, sort_keys=True)
    response = test_client.post(
        '/add_account',
        content_type='application/json',
        data=data
    )
    assert response.status_code == 400
    assert b'fake is not a valid cloud.' in response.data


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_delete_account(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = json.dumps({
        'account_name': 'test',
        'cloud': 'ec2',
        'requesting_user': 'user1'
    }, sort_keys=True)
    response = test_client.post(
        '/delete_account',
        content_type='application/json',
        data=data
    )

    channel.basic.publish.assert_called_once_with(
        body=data,
        routing_key='delete_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"status":"Delete account request submitted."}\n'


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_delete_account_error(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = json.dumps({
        'account_name': 'test',
        'cloud': 'fake',
        'requesting_user': 'user1'
    }, sort_keys=True)
    response = test_client.post(
        '/delete_account',
        content_type='application/json',
        data=data
    )
    assert response.status_code == 400
    assert b"fake is not a valid cloud." in response.data


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.uuid')
@patch('mash.services.api.endpoints.Connection')
def test_api_add_job(mock_connection, mock_uuid, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    uuid = '12345678-1234-1234-1234-123456789012'
    mock_uuid.uuid4.return_value = uuid

    with open('../data/job.json', 'r') as job_doc:
        data = json.load(job_doc)

    del data['job_id']
    response = test_client.post(
        '/add_job',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['job_id'] = uuid
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(data, sort_keys=True),
        routing_key='job_document',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == \
        b'{"job_id": "12345678-1234-1234-1234-123456789012", ' \
        b'"status": "Add job request submitted."}'


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_add_job_error(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    with open('../data/job.json', 'r') as job_doc:
        data = json.load(job_doc)

    response = test_client.post(
        '/add_job',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert b"Additional properties are not allowed " \
        b"(\'job_id\' was unexpected" in response.data


@patch('mash.services.api.endpoints.BaseConfig')
@patch('mash.services.api.endpoints.Connection')
def test_api_delete_job(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    response = test_client.post(
        '/delete_job/12345678-1234-1234-1234-123456789012'
    )

    channel.basic.publish.assert_called_once_with(
        body='{"job_delete": "12345678-1234-1234-1234-123456789012"}',
        routing_key='job_document',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"status":"Delete job request submitted."}\n'
