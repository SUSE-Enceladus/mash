import json

from unittest.mock import patch

from mash.mash_exceptions import MashException


@patch('mash.services.api.v1.routes.jobs.ec2_container.create_container_job')
@patch('mash.services.api.v1.routes.jobs.ec2_container.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_job_ec2_container(
    mock_jwt_required,
    mock_jwt_identity,
    mock_create_container_job,
    test_client
):
    job = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'test',
        'utctime': 'now',
        'errors': []
    }
    mock_create_container_job.return_value = job
    mock_jwt_identity.return_value = 'user1'

    with open('test/data/container_job.json', 'r') as job_doc:
        data = json.load(job_doc)

    del data['requesting_user']
    # del data['job_id']
    # del data['cloud']

    response = test_client.post(
        '/v1/jobs/ec2_container/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    print(f"{response.status_code}")
    print(f"{response.data}")

    assert response.status_code == 201
    assert response.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json['last_service'] == 'test'
    assert response.json['utctime'] == 'now'

    # Dry run
    data['dry_run'] = True
    mock_create_container_job.return_value = None
    response = test_client.post(
        '/v1/jobs/ec2_container/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 200
    assert response.data == b'{"msg":"Job doc is valid!"}\n'

    # Exception
    mock_create_container_job.side_effect = Exception('Broken')

    response = test_client.post(
        '/v1/jobs/ec2_container/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to start job"}\n'

    # Mash Exception
    mock_create_container_job.side_effect = MashException('Broken')

    response = test_client.post(
        '/v1/jobs/ec2_container/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Job failed: Broken"}\n'


def test_api_get_ec2_container_job_schema(test_client):
    response = test_client.get('/v1/jobs/ec2_container/')
    assert response.status_code == 200
    data = json.loads(response.data)  # assert json loads
    assert data['additionalProperties'] is False
