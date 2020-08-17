import json

from unittest.mock import patch

from mash.mash_exceptions import MashException


@patch('mash.services.api.utils.jobs.get_user_by_id')
@patch('mash.services.api.routes.jobs.oci.create_job')
@patch('mash.services.api.utils.jobs.oci.get_oci_account')
@patch('mash.services.api.routes.jobs.oci.get_jwt_identity')
@patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
def test_api_add_job_oci(
    mock_jwt_required,
    mock_jwt_identity,
    mock_get_account,
    mock_create_job,
    mock_get_user,
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
        'start_time': '2011-11-11 11:11:11',
        'state': 'pending',
        'errors': []
    }

    mock_create_job.return_value = job
    mock_jwt_identity.return_value = 'user1'

    account = {
        'region': 'us-phoenix-1',
        'name': 'test-oci',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..'
    }
    mock_get_account.return_value = account

    mock_get_user.return_value = {'email': 'user1@test.com'}

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
    assert response.json['state'] == 'pending'
    assert response.json['start_time'] == '2011-11-11 11:11:11'

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
    mock_get_account.side_effect = Exception('Broken')

    response = test_client.post(
        '/jobs/oci/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.data == b'{"msg":"Failed to start job"}\n'

    # Mash Exception
    mock_get_account.side_effect = MashException('Broken')

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
