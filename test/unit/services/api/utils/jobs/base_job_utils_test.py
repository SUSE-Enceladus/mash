import json

from pytest import raises
from unittest.mock import Mock, patch

from mash.services.api.utils.jobs import (
    create_job,
    delete_job,
    get_job,
    get_jobs
)


@patch('mash.services.api.utils.jobs.Job')
@patch('mash.services.api.utils.jobs.publish')
@patch('mash.services.api.utils.jobs.db')
@patch('mash.services.api.utils.jobs.get_user_by_id')
@patch('mash.services.api.utils.jobs.uuid')
def test_create_job(mock_uuid, mock_get_user, mock_db, mock_publish, mock_job):
    job = Mock()
    user = Mock()
    user.id = '1'

    mock_uuid.uuid4.return_value = '12345678-1234-1234-1234-123456789012'
    mock_get_user.return_value = user
    mock_job.return_value = job

    data = {
        'last_service': 'testing',
        'utctime': 'now',
        'image': 'test_oem_image',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server',
        'requesting_user': '1'
    }

    result = create_job(data)
    data['job_id'] = '12345678-1234-1234-1234-123456789012'

    assert result == job
    mock_db.session.add.assert_called_once_with(job)
    mock_publish.assert_called_once_with(
        'jobcreator',
        'job_document',
        json.dumps(data, sort_keys=True)
    )
    mock_db.session.commit.assert_called_once_with()

    # Exception
    mock_publish.side_effect = Exception('Cannot publish message!')
    del data['job_id']

    with raises(Exception):
        create_job(data)

    mock_db.session.rollback.assert_called_once_with()


@patch('mash.services.api.utils.jobs.Job')
def test_get_job(mock_job):
    job = Mock()
    queryset = Mock()
    queryset1 = Mock()
    queryset1.first.return_value = job
    queryset.filter_by.return_value = queryset1
    mock_job.query.filter.return_value = queryset

    assert get_job('12345678-1234-1234-1234-123456789012', '1') == job


@patch('mash.services.api.utils.jobs.get_user_by_id')
def test_get_jobs(mock_get_user):
    job = Mock()
    user = Mock()
    user.jobs = [job]
    mock_get_user.return_value = user

    assert get_jobs('1') == [job]


@patch('mash.services.api.utils.jobs.publish')
@patch('mash.services.api.utils.jobs.db')
@patch('mash.services.api.utils.jobs.get_job')
def test_delete_jobs(mock_get_job, mock_db, mock_publish):
    job = Mock()
    mock_get_job.return_value = job

    assert delete_job('12345678-1234-1234-1234-123456789012', '1') == 1
    mock_db.session.delete.assert_called_once_with(job)
    mock_db.session.commit.assert_called_once_with()
    mock_publish.assert_called_once_with(
        'jobcreator',
        'job_document',
        json.dumps({'job_delete': '12345678-1234-1234-1234-123456789012'}, sort_keys=True)
    )

    # Exception
    mock_db.session.delete.side_effect = Exception("Unable to delete job!")

    with raises(Exception):
        delete_job('12345678-1234-1234-1234-123456789012', '1')

    mock_db.session.rollback.assert_called_once_with()

    # Not found
    mock_get_job.return_value = None
    assert delete_job('12345678-1234-1234-1234-123456789012', '1') == 0
