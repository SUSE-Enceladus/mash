import json
import pytest

from unittest.mock import patch

from mash.services.credentials.app import create_app
from mash.services.credentials.flask_config import Config


@pytest.fixture(scope='module')
def test_client():
    flask_config = Config(
        config_file='test/data/mash_config.yaml',
        test=True
    )
    application = create_app(flask_config)
    test_client = application.test_client()

    ctx = application.app_context()
    ctx.push()

    yield test_client
    ctx.pop()


@patch('mash.services.credentials.routes.credentials.current_app')
def test_add_credentials(mock_app, test_client):
    data = {
        "cloud": "ec2",
        "account_name": "test-aws",
        "requesting_user": "user1",
        "credentials": {
            "super": "secret"
        }
    }

    response = test_client.post(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_app.credentials_datastore.save_credentials.assert_called_once_with(
        'ec2',
        'test-aws',
        'user1',
        {'super': 'secret'}
    )
    assert response.status_code == 201
    assert response.data == b'{"msg":"Credentials saved"}\n'

    # Error
    mock_app.credentials_datastore.save_credentials.side_effect = Exception(
        'Permission denied'
    )

    response = test_client.post(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_app.logger.warning.assert_called_once_with(
        'Unable to save credentials: Permission denied'
    )
    assert response.status_code == 400
    assert response.data == \
        b'{"msg":"Unable to save credentials: Permission denied"}\n'


@patch('mash.services.credentials.routes.credentials.current_app')
def test_get_credentials(mock_app, test_client):
    creds = {'test-aws': {'super': 'secret'}}
    data = {
        'cloud': 'ec2',
        'cloud_accounts': ['test-aws'],
        'requesting_user': 'user1'
    }
    mock_app.credentials_datastore.retrieve_credentials.return_value = creds

    response = test_client.get(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"test-aws":{"super":"secret"}}\n'

    # Error
    mock_app.credentials_datastore.retrieve_credentials.side_effect = \
        Exception('Permission denied')

    response = test_client.get(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    mock_app.logger.warning.assert_called_once_with(
        'Unable to retrieve credentials: Permission denied'
    )
    assert response.status_code == 400
    assert response.data == \
        b'{"msg":"Unable to retrieve credentials: Permission denied"}\n'


@patch('mash.services.credentials.routes.credentials.current_app')
def test_delete_credentials(mock_app, test_client):
    job_doc = {
        "cloud": "ec2",
        "account_name": "test-aws",
        "requesting_user": "user1"
    }

    response = test_client.delete(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(job_doc, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.data == b'{"msg":"Credentials deleted"}\n'

    # Error
    mock_app.credentials_datastore.delete_credentials.side_effect = Exception(
        'Permission denied'
    )

    response = test_client.delete(
        '/credentials/',
        content_type='application/json',
        data=json.dumps(job_doc, sort_keys=True)
    )

    mock_app.logger.warning.assert_called_once_with(
        'Unable to delete credentials: Permission denied'
    )
    assert response.status_code == 400
    assert response.data == \
        b'{"msg":"Unable to delete credentials: Permission denied"}\n'


@patch('mash.services.credentials.routes.credentials.current_app')
def test_delete_user(mock_app, test_client):
    response = test_client.delete('credentials/fakeuser101')

    assert response.status_code == 200
    assert response.data == b'{"msg":"User removed"}\n'

    # Error
    mock_app.credentials_datastore.remove_user.side_effect = Exception(
        'Permission denied'
    )
    response = test_client.delete('credentials/fakeuser101')

    mock_app.logger.warning.assert_called_once_with(
        'Unable to remove all credentials for user: Permission denied'
    )
    assert response.status_code == 400
    assert response.data == \
        b'{"msg":"Unable to remove all credentials for user: Permission denied"}\n'
