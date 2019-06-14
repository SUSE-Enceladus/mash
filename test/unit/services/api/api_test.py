import json
import pytest

from unittest.mock import MagicMock, patch

from mash.services.api import wsgi


@pytest.fixture(scope='module')
def test_client():
    testing_client = wsgi.application.test_client()

    ctx = wsgi.application.app_context()
    ctx.push()

    yield testing_client
    ctx.pop()


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_account_ec2(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    request = {
        'account_name': 'test',
        'credentials': {
            'access_key_id': '123456',
            'secret_access_key': '654321'
        },
        'group': 'group1',
        'partition': 'aws',
        'region': 'us-east-1',
        'requesting_user': 'user1'
    }
    response = test_client.post(
        '/accounts/ec2/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    request['cloud'] = 'ec2'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(request, sort_keys=True),
        routing_key='add_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 201
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_account_gce(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    request = {
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
        'group': 'group1',
        'bucket': 'bucket1',
        'region': 'us-east-1',
        'requesting_user': 'user1'
    }
    response = test_client.post(
        '/accounts/gce/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    request['cloud'] = 'gce'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(request, sort_keys=True),
        routing_key='add_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 201
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_account_azure(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    request = {
        'account_name': 'test',
        'group': 'group1',
        'region': 'us-east-1',
        'requesting_user': 'user1',
        "source_container": "string",
        "source_resource_group": "string",
        "source_storage_account": "string",
        "destination_container": "string",
        "destination_resource_group": "string",
        "destination_storage_account": "string",
        "credentials": {
            "clientId": "string",
            "clientSecret": "string",
            "subscriptionId": "string",
            "tenantId": "string",
            "activeDirectoryEndpointUrl": "string",
            "resourceManagerEndpointUrl": "string",
            "activeDirectoryGraphResourceId": "string",
            "sqlManagementEndpointUrl": "string",
            "galleryEndpointUrl": "string",
            "managementEndpointUrl": "string"
        }
    }
    response = test_client.post(
        '/accounts/azure/',
        content_type='application/json',
        data=json.dumps(request, sort_keys=True)
    )

    request['cloud'] = 'azure'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(request, sort_keys=True),
        routing_key='add_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 201
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_delete_account_ec2(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = {
        'requesting_user': 'user1'
    }
    response = test_client.delete(
        '/accounts/ec2/test',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['cloud'] = 'ec2'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(data, sort_keys=True),
        routing_key='delete_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_delete_account_gce(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = {
        'requesting_user': 'user1'
    }
    response = test_client.delete(
        '/accounts/gce/test',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['cloud'] = 'gce'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(data, sort_keys=True),
        routing_key='delete_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
def test_api_delete_account_azure(mock_connection, mock_config, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    config = MagicMock()
    config.get_amqp_host.return_value = 'localhost'
    config.get_amqp_user.return_value = 'guest'
    config.get_amqp_pass.return_value = 'guest'
    mock_config.return_value = config

    data = {
        'requesting_user': 'user1'
    }
    response = test_client.delete(
        '/accounts/azure/test',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['cloud'] = 'azure'
    channel.basic.publish.assert_called_once_with(
        body=json.dumps(data, sort_keys=True),
        routing_key='delete_account',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == b'{"name":"test"}\n'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.jobs.uuid')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_job_ec2(mock_connection, mock_uuid, mock_config, test_client):
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
    del data['cloud']
    response = test_client.post(
        '/jobs/ec2/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['job_id'] = uuid
    data['cloud'] = 'ec2'
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
    assert response.status_code == 201
    assert response.data == \
        b'{"job_id": "12345678-1234-1234-1234-123456789012"}'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.jobs.uuid')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_job_gce(mock_connection, mock_uuid, mock_config, test_client):
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

    with open('../data/gce_job.json', 'r') as job_doc:
        data = json.load(job_doc)

    del data['job_id']
    del data['cloud']
    response = test_client.post(
        '/jobs/gce/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['job_id'] = uuid
    data['cloud'] = 'gce'
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
    assert response.status_code == 201
    assert response.data == \
        b'{"job_id": "12345678-1234-1234-1234-123456789012"}'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.jobs.uuid')
@patch('mash.services.api.routes.utils.Connection')
def test_api_add_job_azure(mock_connection, mock_uuid, mock_config, test_client):
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

    with open('../data/azure_job.json', 'r') as job_doc:
        data = json.load(job_doc)

    del data['job_id']
    del data['cloud']
    response = test_client.post(
        '/jobs/azure/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    data['job_id'] = uuid
    data['cloud'] = 'azure'
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
    assert response.status_code == 201
    assert response.data == \
        b'{"job_id": "12345678-1234-1234-1234-123456789012"}'


@patch('mash.services.api.routes.utils.BaseConfig')
@patch('mash.services.api.routes.utils.Connection')
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

    response = test_client.delete(
        '/jobs/12345678-1234-1234-1234-123456789012'
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
    assert response.data == \
        b'{"job_id":"12345678-1234-1234-1234-123456789012"}\n'
