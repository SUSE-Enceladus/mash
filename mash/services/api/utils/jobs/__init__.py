# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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

from mash.services.api.extensions import db
from mash.services.api.models import Job, User
from mash.services.api.utils.amqp import publish
from mash.services.api.utils.users import get_user_by_id


def get_new_job_id():
    return str(uuid.uuid4())


def create_job(data):
    """
    Create a new job for user.
    """
    job_id = get_new_job_id()
    data['job_id'] = job_id

    user_id = data['requesting_user']

    kwargs = {
        'job_id': job_id,
        'last_service': data['last_service'],
        'utctime': data['utctime'],
        'image': data['image'],
        'download_url': data['download_url'],
        'user_id': user_id
    }

    if data.get('cloud_architecture'):
        kwargs['cloud_architecture'] = data['cloud_architecture']

    if data.get('profile'):
        kwargs['profile'] = data['profile']

    job = Job(**kwargs)

    try:
        db.session.add(job)
        publish(
            'jobcreator', 'job_document', json.dumps(data, sort_keys=True)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return job


def get_job(job_id, user_id):
    """
    Get job for given user.
    """
    job = Job.query.filter(
        User.id == user_id
    ).filter_by(job_id=job_id).first()

    return job


def get_jobs(user_id):
    """
    Retrieve all jobs for user.
    """
    user = get_user_by_id(user_id)
    return user.jobs


def delete_job(job_id, user_id):
    """Delete job for user."""
    job = get_job(job_id, user_id)

    if job:
        try:
            db.session.delete(job)
            publish(
                'jobcreator',
                'job_document',
                json.dumps({'job_delete': job_id}, sort_keys=True)
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return 1
    else:
        return 0
