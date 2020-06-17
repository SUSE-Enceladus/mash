import json

from unittest.mock import Mock, patch

from mash.mash_exceptions import MashException


@patch('mash.services.api.routes.jobs.oci.create_job')
@patch('mash.services.api.routes.jobs.oci.validate_oci_job')
@patch('mash.services.api.routes.jobs.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_job_oci(
        mock_jwt_required,
        mock_jwt_identity,
        mock_validate_oci_job,
        mock_create_job,
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

    mock_create_job.return_value = job
    mock_jwt_identity.return_value = 'user1'

    with open('test/data/oci_job.json', 'r') as job_doc:
        data = json.load(job_doc)

    del data['requesting_user']
    del data['job_id']
    del data['cloud']
    del data['oci_user_id']
    del data['tenancy']

    response = test_client.post(
        '/jobs/oci/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 201
    assert response.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json['last_service'] == 'test'
    assert response.json['utctime'] == 'now'
    assert response.json['image'] == 'test_image_oem'
    assert response.json['download_url'] == 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    assert response.json['cloud_architecture'] == 'x86_64'
    assert response.json['profile'] == 'Server'

    # Dry run
    data['dry_run'] = True
    mock_create_job.return_value = None
    response = test_client.post(
        '/jobs/oci/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{"msg":"Job doc is valid!"}\n'

    # Exception
    mock_validate_oci_job.side_effect = Exception('Broken')

    response = test_client.post(
        '/jobs/oci/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to start job"}\n'

    # Mash Exception
    mock_validate_oci_job.side_effect = MashException('Broken')

    response = test_client.post(
        '/jobs/oci/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Job failed: Broken"}\n'


def test_api_get_oci_job_schema(test_client):
    response = test_client.get('/jobs/oci/')
    assert response.status_code == 200
    data = json.loads(response.data)  # assert json loads
    assert data['additionalProperties'] is False
