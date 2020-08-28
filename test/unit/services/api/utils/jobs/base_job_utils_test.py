import json

from pytest import raises
from unittest.mock import Mock, patch

from mash.services.api.utils.jobs import (
    create_job,
    delete_job,
    validate_last_service,
    validate_create_args,
    validate_deprecate_args
)
from mash.mash_exceptions import MashJobException

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.jobs.publish')
@patch('mash.services.api.utils.jobs.handle_request')
@patch('mash.services.api.utils.jobs.get_user_by_id')
@patch('mash.services.api.utils.jobs.uuid')
def test_create_job(
    mock_uuid,
    mock_get_user,
    mock_handle_request,
    mock_publish,
    mock_get_current_obj
):
    app = Mock()
    app.config = {
        'DATABASE_API_URL': 'http://localhost:5007',
        'SERVICE_NAMES': [
            'obs',
            'uploader',
            'create',
            'testing',
            'raw_image_uploader',
            'replication',
            'publisher',
            'deprecation'
        ]
    }
    mock_get_current_obj.return_value = app

    mock_uuid.uuid4.return_value = '12345678-1234-1234-1234-123456789012'

    user = {'id': '1'}
    mock_get_user.return_value = user

    job = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test_oem_image',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'cloud_image_name': 'Test OEM Image',
        'old_cloud_image_name': 'Old test OEM Image',
        'image_description': 'Description of an image',
        'profile': 'Server',
        'start_time': '2011-11-11 11:11:11',
        'state': 'pending'
    }

    response = Mock()
    response.json.return_value = job
    mock_handle_request.return_value = response

    data = {
        'last_service': 'deprecate',
        'utctime': '2019-04-28T06:44:50.142Z',
        'image': 'test_oem_image',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server',
        'requesting_user': '1',
        'cloud_image_name': 'Test OEM Image',
        'old_cloud_image_name': 'Old test OEM Image',
        'image_description': 'Description of an image'
    }

    result = create_job(data)
    data['job_id'] = '12345678-1234-1234-1234-123456789012'

    assert result == job
    mock_publish.assert_called_once_with(
        'jobcreator',
        'job_document',
        json.dumps(data, sort_keys=True)
    )

    # Exception
    mock_publish.side_effect = Exception('Cannot publish message!')
    mock_handle_request.side_effect = [None, Exception('Borked')]
    del data['job_id']

    with raises(Exception):
        create_job(data)

    # Dry run
    data['dry_run'] = True
    result = create_job(data)
    assert result is None


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.jobs.publish')
@patch('mash.services.api.utils.jobs.handle_request')
def test_delete_jobs(mock_handle_request, mock_publish, mock_get_current_obj):
    job = {'rows_deleted': 1}
    response = Mock()
    response.json.return_value = job
    mock_handle_request.return_value = response
    mock_publish.side_effect = Exception('Broken')

    app = Mock()
    app.config = {
        'DATABASE_API_URL': 'http://localhost:5007',
    }
    mock_get_current_obj.return_value = app

    assert delete_job('12345678-1234-1234-1234-123456789012', '1') == 1

    # Exception
    del job['rows_deleted']

    with raises(MashJobException):
        delete_job('12345678-1234-1234-1234-123456789012', '1')


@patch.object(LocalProxy, '_get_current_object')
def test_validate_last_service(mock_get_current_obj):
    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'obs',
            'uploader',
            'create',
            'testing',
            'raw_image_uploader',
            'replication',
            'publisher',
            'deprecation'
        ]
    }
    mock_get_current_obj.return_value = app

    data = {
        'last_service': 'fake'
    }

    with raises(MashJobException):
        validate_last_service(data)


def test_validate_create_args():
    with raises(MashJobException):
        validate_create_args({})


def test_validate_deprecate_args():
    with raises(MashJobException):
        validate_deprecate_args({})
