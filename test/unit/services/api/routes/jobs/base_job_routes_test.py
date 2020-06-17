from unittest.mock import Mock, patch


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
    assert response.data == b'{"msg":"Delete job failed"}\n'


@patch('mash.services.api.routes.jobs.get_job')
@patch('mash.services.api.routes.jobs.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_job(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_job,
        test_client
):
    job = Mock()
    job.job_id = '12345678-1234-1234-1234-123456789012'
    job.last_service = 'test'
    job.utctime = 'now'
    job.image = 'test_image_oem'
    job.download_url = 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    job.cloud_architecture = 'x86_64'
    job.profile = 'Server'

    mock_get_job.return_value = job
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )

    assert response.status_code == 200
    assert response.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json['last_service'] == 'test'
    assert response.json['utctime'] == 'now'
    assert response.json['image'] == 'test_image_oem'
    assert response.json['download_url'] == 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    assert response.json['cloud_architecture'] == 'x86_64'
    assert response.json['profile'] == 'Server'

    # Not found
    mock_get_job.return_value = None

    response = test_client.get(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )
    assert response.status_code == 404
    assert response.data == b'{"msg":"Job not found"}\n'


@patch('mash.services.api.routes.jobs.get_jobs')
@patch('mash.services.api.routes.jobs.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_get_job_list(
        mock_jwt_required,
        mock_jwt_identity,
        mock_get_jobs,
        test_client
):
    job = Mock()
    job.job_id = '12345678-1234-1234-1234-123456789012'
    job.last_service = 'test'
    job.utctime = 'now'
    job.image = 'test_image_oem'
    job.download_url = 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    job.cloud_architecture = 'x86_64'
    job.profile = 'Server'

    mock_get_jobs.return_value = [job]
    mock_jwt_identity.return_value = 'user1'

    response = test_client.get('/jobs/')

    assert response.status_code == 200
    assert response.json[0]['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json[0]['last_service'] == 'test'
    assert response.json[0]['utctime'] == 'now'
    assert response.json[0]['image'] == 'test_image_oem'
    assert response.json[0]['download_url'] == 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    assert response.json[0]['cloud_architecture'] == 'x86_64'
    assert response.json[0]['profile'] == 'Server'
