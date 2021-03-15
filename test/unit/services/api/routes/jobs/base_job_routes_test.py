import json

from datetime import datetime
from unittest.mock import patch, Mock


@patch('mash.services.api.routes.jobs.delete_job')
@patch('mash.services.api.routes.jobs.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_delete_job(
        mock_jwt_required,
        mock_jwt_identity,
        mock_delete_job,
        test_client
):
    mock_delete_job.return_value = 1
    mock_jwt_identity.return_value = 'user1'

    response = test_client.delete(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )

    assert response.status_code == 200
    assert response.data == b'{"msg":"Job deletion request submitted"}\n'

    # Not found
    mock_delete_job.return_value = 0

    response = test_client.delete(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"Job not found"}\n'

    # Exception
    mock_delete_job.side_effect = Exception('Broken')

    response = test_client.delete(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Broken"}\n'


@patch('mash.services.api.utils.jobs.handle_request')
@patch('mash.services.api.routes.jobs.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_job(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    job = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test_image_oem',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server',
        'start_time': str(datetime(2011, 11, 11, 11, 11, 11)),
        'state': 'pending',
        'errors': []
    }
    response = Mock()
    response.json.return_value = job
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )

    assert result.status_code == 200
    assert result.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert result.json['last_service'] == 'test'
    assert result.json['utctime'] == 'now'
    assert result.json['image'] == 'test_image_oem'
    assert result.json['download_url'] == 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    assert result.json['cloud_architecture'] == 'x86_64'
    assert result.json['profile'] == 'Server'
    assert result.json['state'] == 'pending'
    assert result.json['start_time'] == '2011-11-11 11:11:11'

    # Not found
    response.json.return_value = {}

    result = test_client.get(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )
    assert result.status_code == 404
    assert result.data == b'{"msg":"Job not found"}\n'


@patch('mash.services.api.utils.jobs.handle_request')
@patch('mash.services.api.routes.jobs.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_job_list(
        mock_jwt_required,
        mock_jwt_identity,
        mock_handle_request,
        test_client
):
    job = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test_image_oem',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server',
        'start_time': str(datetime(2011, 11, 11, 11, 11, 11)),
        'state': 'pending',
        'errors': []
    }
    response = Mock()
    response.json.return_value = [job]
    mock_handle_request.return_value = response

    mock_jwt_identity.return_value = 'user1'

    result = test_client.get(
        '/jobs/',
        content_type='application/json',
        data=json.dumps({'page': 1, 'per_page': 10})
    )

    assert result.status_code == 200
    assert result.json[0]['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert result.json[0]['last_service'] == 'test'
    assert result.json[0]['utctime'] == 'now'
    assert result.json[0]['image'] == 'test_image_oem'
    assert result.json[0]['download_url'] == 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    assert result.json[0]['cloud_architecture'] == 'x86_64'
    assert result.json[0]['profile'] == 'Server'
    assert result.json[0]['state'] == 'pending'
    assert result.json[0]['start_time'] == '2011-11-11 11:11:11'
