import json
import pytest

from unittest.mock import patch

from mash.services.credentials.app import create_app
from mash.services.credentials.flask_config import Config


@pytest.fixture(scope='module')
def test_client():
    flask_config = Config(
        config_file='../data/mash_config.yaml',
        testing=True
    )
    application = create_app(flask_config)
    testing_client = application.test_client()

    ctx = application.app_context()
    ctx.push()

    yield testing_client
    ctx.pop()


@patch('mash.services.credentials.routes.jobs.save_job')
@patch('mash.services.credentials.routes.jobs.current_app')
def test_add_job(mock_app, mock_save_job, test_client):
    mock_app.jobs = {}
    job_doc = {
        "credentials_job": {
            "id": "123",
            "cloud": "ec2",
            "cloud_accounts": ["test-aws"],
            "requesting_user": "user1",
            "last_service": "deprecation",
            "utctime": "now",
            "notification_email": "test@fake.com",
            "notification_type": "single"
        }
    }

    response = test_client.post(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(job_doc, sort_keys=True)
    )

    mock_app.logger.info.assert_called_once_with(
        'Job queued, awaiting credentials requests.',
        extra={'job_id': '123'}
    )
    assert mock_save_job.call_count == 1
    assert response.status_code == 201
    assert response.data == b'{"msg":"Job added"}\n'
    assert '123' in mock_app.jobs

    # Job exists
    mock_app.logger.info.reset_mock()
    mock_app.jobs = {'123': {'job': 'info'}}

    response = test_client.post(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(job_doc, sort_keys=True)
    )

    mock_app.logger.info.assert_called_once_with(
        'Job exists',
        extra={'job_id': '123'}
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Job exists"}\n'

    # Error
    mock_app.jobs = {}
    mock_save_job.side_effect = Exception('Job invalid')

    response = test_client.post(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(job_doc, sort_keys=True)
    )

    mock_app.logger.warning.assert_called_once_with(
        'Unable to add job: Job invalid',
        extra={'job_id': '123'}
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to add job: Job invalid"}\n'


@patch('mash.services.credentials.routes.jobs.remove_job')
@patch('mash.services.credentials.routes.jobs.current_app')
def test_delete_job(mock_app, mock_remove_job, test_client):
    mock_app.jobs = {'123': {'job': 'info'}}

    response = test_client.delete('/jobs/123')

    mock_app.logger.info.assert_called_once_with(
        'Deleting job.',
        extra={'job_id': '123'}
    )
    assert mock_remove_job.call_count == 1
    assert response.status_code == 200
    assert response.data == b'{"msg":"Job deleted"}\n'
    assert '123' not in mock_app.jobs

    # Error
    mock_app.jobs = {'123': {'job': 'info'}}
    mock_remove_job.side_effect = Exception('Delete failed')

    response = test_client.delete('/jobs/123')

    mock_app.logger.warning.assert_called_once_with(
        'Unable to delete job: Delete failed',
        extra={'job_id': '123'}
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to delete job: Delete failed"}\n'

    # Job does not exist
    mock_app.logger.warning.reset_mock()
    mock_app.jobs = {}

    response = test_client.delete('/jobs/123')

    mock_app.logger.warning.assert_called_once_with(
        'Job does not exist',
        extra={'job_id': '123'}
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"Job does not exist"}\n'
