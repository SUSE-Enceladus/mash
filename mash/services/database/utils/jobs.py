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

from datetime import datetime

from mash.services.database.extensions import db
from mash.services.database.models import Job
from mash.services.status_levels import FAILED, EXCEPTION, RUNNING, FINISHED


def create_new_job(data):
    """
    Create a new job for user.
    """
    job = Job(**data)

    try:
        db.session.add(job)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return job


def get_job(job_id):
    """
    Get job.
    """
    return Job.query.filter_by(job_id=job_id).first()


def get_job_by_user(job_id, user_id):
    """
    Get job for given user.
    """
    job = Job.query.filter_by(
        user_id=user_id,
        job_id=job_id
    ).first()

    return job


def get_jobs(user_id, page=1, per_page=10):
    """
    Retrieve all jobs for user.
    """
    job_query = Job.query.filter_by(user_id=user_id).paginate(
        page=page,
        per_page=per_page,
        error_out=False,  # Return empty set if no results
        max_per_page=20
    )
    return job_query.items


def delete_job_for_user(job_id, user_id):
    """Delete job for user."""
    job = get_job_by_user(job_id, user_id)

    if job:
        try:
            db.session.delete(job)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return 1
    else:
        return 0


def save_job_status(job_doc):
    """
    Update job in database with new status.

    The status is updated when each service finishes.
    """
    job = get_job(job_doc.pop('id'))
    job.prev_service = job_doc.pop('prev_service')

    status = job_doc.pop('status')
    current_service = job_doc.pop('current_service')

    failed_states = (FAILED, EXCEPTION)
    if status in failed_states and job.state != status:
        job.failed_service = job.prev_service
        job.state = status

    if job.prev_service == job.last_service:
        job.finish_time = datetime.utcnow()
        job.current_service = None

        if job.state == RUNNING:
            job.state = FINISHED
    else:
        job.current_service = current_service

    job.errors = job_doc.pop('errors', [])
    job.data = job_doc

    try:
        db.session.add(job)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
