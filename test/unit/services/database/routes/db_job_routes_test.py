# Copyright (c) 2020 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import json

from datetime import datetime
from unittest.mock import patch, Mock


@patch('mash.services.database.utils.jobs.db')
def test_create_job(mock_db, test_client):
    data = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'deprecate',
        'utctime': 'now',
        'image': 'test_oem_image',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server'
    }

    response = test_client.post(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json['image'] == 'test_oem_image'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.post(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to create job: Broken"}\n'


@patch('mash.services.database.utils.jobs.get_job')
@patch('mash.services.database.utils.jobs.db')
def test_update_job_status(mock_db, mock_get_job, test_client):
    job = Mock()
    job.state = 'running'
    job.last_service = 'deprecate'
    mock_get_job.return_value = job

    data = {
        'id': '12345678-1234-1234-1234-123456789012',
        'last_service': 'deprecate',
        'utctime': 'now',
        'image': 'test_oem_image',
        'download_url': 'http://download.opensuse.org/repositories/Cloud:Tools/images',
        'cloud_architecture': 'x86_64',
        'profile': 'Server',
        'state': 'running',
        'status': 'success',
        'current_service': None,
        'prev_service': 'deprecate'
    }

    response = test_client.put(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['msg'] == 'Job status updated'

    # Job failed
    data['status'] = 'failed'
    data['current_service'] = 'raw_image_upload'
    data['prev_service'] = 'test'
    response = test_client.put(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['msg'] == 'Job status updated'

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.put(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    mock_db.session.rollback.assert_called_once_with()
    assert response.status_code == 400
    assert response.data == b'{"msg":"Unable to update job status: Broken"}\n'


@patch('mash.services.database.utils.jobs.Job')
def test_get_job(mock_job, test_client):
    job = Mock()
    job.job_id = '12345678-1234-1234-1234-123456789012'
    job.last_service = 'test'
    job.utctime = 'now'
    job.image = 'test_image_oem'
    job.download_url = 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    job.cloud_architecture = 'x86_64'
    job.profile = 'Server'
    job.start_time = datetime.now()
    job.finish_time = datetime.now()
    job.errors = []

    queryset1 = Mock()
    queryset1.first.return_value = job
    mock_job.query.filter_by.return_value = queryset1

    data = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'user_id': 'user1'
    }

    response = test_client.get(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json['image'] == 'test_image_oem'
    assert response.json['profile'] == 'Server'

    # Mash Exception
    queryset1.first.side_effect = Exception('Broken')

    response = test_client.get(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    msg = (
        'Unable to get job 12345678-1234-1234-1234-123456789012'
        ' for user user1: Broken'
    )
    assert response.json['msg'] == msg


@patch('mash.services.database.utils.jobs.Job')
def test_get_job_list(mock_job, test_client):
    job = Mock()
    job.job_id = '12345678-1234-1234-1234-123456789012'
    job.last_service = 'test'
    job.utctime = 'now'
    job.image = 'test_image_oem'
    job.download_url = 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    job.cloud_architecture = 'x86_64'
    job.profile = 'Server'
    job.start_time = datetime.now()
    job.finish_time = datetime.now()
    job.errors = []

    queryset1 = Mock()
    queryset2 = Mock()
    queryset2.items = [job]
    queryset1.paginate.return_value = queryset2
    mock_job.query.filter_by.return_value = queryset1

    response = test_client.get(
        '/jobs/list/user1',
        content_type='application/json',
        data=json.dumps({'page': 1, 'per_page': 10})
    )

    assert response.status_code == 200
    assert response.json[0]['job_id'] == '12345678-1234-1234-1234-123456789012'
    assert response.json[0]['image'] == 'test_image_oem'
    assert response.json[0]['profile'] == 'Server'


@patch('mash.services.database.utils.jobs.db')
@patch('mash.services.database.utils.jobs.get_job_by_user')
def test_delete_job(mock_get_job, mock_db, test_client):
    job = Mock()
    job.job_id = '12345678-1234-1234-1234-123456789012'
    job.last_service = 'test'
    job.utctime = 'now'
    job.image = 'test_image_oem'
    job.download_url = 'http://download.opensuse.org/repositories/Cloud:Tools/images'
    job.cloud_architecture = 'x86_64'
    job.profile = 'Server'
    job.start_time = datetime.now()
    job.finish_time = datetime.now()
    job.errors = []

    mock_get_job.return_value = job

    data = {
        'job_id': '12345678-1234-1234-1234-123456789012',
        'user_id': 'user1'
    }

    response = test_client.delete(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['rows_deleted'] == 1

    # Mash Exception
    mock_db.session.commit.side_effect = Exception('Broken')

    response = test_client.delete(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )
    assert response.status_code == 400
    assert response.json['msg'] == 'Delete job failed'

    # No job found
    mock_get_job.return_value = None

    response = test_client.delete(
        '/jobs/',
        content_type='application/json',
        data=json.dumps(data, sort_keys=True)
    )

    assert response.status_code == 200
    assert response.json['rows_deleted'] == 0
