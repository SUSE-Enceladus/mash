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
import uuid

from dateutil import parser
from flask import current_app

from mash.services.api.utils.amqp import publish
from mash.mash_exceptions import MashJobException
from mash.utils.mash_utils import normalize_dictionary
from mash.services.status_levels import RUNNING
from mash.utils.mash_utils import handle_request
from mash.services.api.utils.users import get_user_by_id


def get_new_job_id():
    return str(uuid.uuid4())


def create_job(data):
    """
    Create a new job for user.
    """
    if data.get('dry_run'):
        return None

    job_id = get_new_job_id()
    data['job_id'] = job_id

    user_id = data['requesting_user']

    kwargs = {
        'job_id': job_id,
        'last_service': data['last_service'],
        'utctime': data['utctime'],
        'image': data['image'],
        'download_url': data['download_url'],
        'user_id': user_id,
        'state': RUNNING,
        'current_service': current_app.config['SERVICE_NAMES'][0]
    }

    if data['utctime'] not in ('now', 'always'):
        kwargs['start_time'] = parser.parse(data['utctime'])

    if data.get('cloud_architecture'):
        kwargs['cloud_architecture'] = data['cloud_architecture']

    if data.get('profile'):
        kwargs['profile'] = data['profile']

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'jobs/',
        'post',
        job_data=kwargs
    )

    try:
        publish(
            'jobcreator',
            'job_document',
            json.dumps(data, sort_keys=True)
        )
    except Exception:
        try:
            handle_request(
                current_app.config['DATABASE_API_URL'],
                'jobs/',
                'delete',
                job_data={'job_id': job_id, 'user_id': user_id}
            )
        except Exception:
            pass  # Attempt to cleanup job in database

        raise MashJobException('Failed to initialize job.')

    return response.json()


def validate_job(data):
    """
    Validate job doc.
    """
    data = normalize_dictionary(data)
    validate_last_service(data)
    services_run = get_services_by_last_service(data['last_service'])

    if 'create' in services_run:
        validate_create_args(data)

    if 'deprecate' in services_run:
        validate_deprecate_args(data)

    if 'notification_type' in data and not data.get('notification_email'):
        user_id = data['requesting_user']
        user = get_user_by_id(user_id)
        data['notification_email'] = user['email']

    return data


def validate_last_service(data):
    """
    Validate last service is a valid service name.
    """
    if data['last_service'] not in current_app.config['SERVICE_NAMES']:
        raise MashJobException(
            'The service name {name} is invalid. '
            'Valid service names are: {services}.'.format(
                name=data['last_service'],
                services=', '.join(current_app.config['SERVICE_NAMES'])
            )
        )


def validate_create_args(data):
    """
    Validate required args for image creation jobs.
    """
    required_args = ['cloud_image_name', 'image_description']

    for required_arg in required_args:
        if required_arg not in data:
            raise MashJobException(
                'Jobs that perform image creation require {arg_name} '
                'in the job doc.'.format(
                    arg_name=required_arg
                )
            )


def validate_deprecate_args(data):
    """
    Validate required args for image deprecate jobs.
    """
    if 'old_cloud_image_name' not in data:
        raise MashJobException(
            'Jobs that perform image deprecate require '
            'old_cloud_image_name in the job doc.'
        )


def get_services_by_last_service(last_service):
    """
    Returns a list of service names that will run based on last service.
    """
    index = current_app.config['SERVICE_NAMES'].index(last_service)
    return current_app.config['SERVICE_NAMES'][:index + 1]


def get_job(job_id, user_id):
    """
    Get job for given user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'jobs/',
        'get',
        job_data={'job_id': job_id, 'user_id': user_id}
    )

    return response.json()


def get_jobs(user_id):
    """
    Retrieve all jobs for user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'jobs/list/{user}'.format(user=user_id),
        'get'
    )

    return response.json()


def delete_job(job_id, user_id):
    """Delete job for user."""
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'jobs/',
        'delete',
        job_data={'job_id': job_id, 'user_id': user_id}
    )

    try:
        rows_deleted = response.json()['rows_deleted']
    except KeyError:
        raise MashJobException('Delete job failed')

    try:
        publish(
            'jobcreator',
            'job_document',
            json.dumps({'job_delete': job_id}, sort_keys=True)
        )
    except Exception:
        pass  # We cannot always cleanup the job from the queue

    return rows_deleted
