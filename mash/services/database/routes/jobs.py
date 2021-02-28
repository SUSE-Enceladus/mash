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

from flask import Blueprint, current_app, jsonify, request, make_response
from flask_restplus import marshal, fields, Model

from mash.services.database.utils.jobs import (
    save_job_status,
    get_job_by_user,
    get_jobs,
    delete_job_for_user,
    create_new_job
)

blueprint = Blueprint('jobs', __name__, url_prefix='/jobs')

job_data = Model(
    'job_data', {
        '*': fields.Wildcard(fields.String)
    }
)

job_response = Model(
    'job_response', {
        'job_id': fields.String(
            example='12345678-1234-1234-1234-123456789012'
        ),
        'last_service': fields.String(example='test'),
        'current_service': fields.String(example='test'),
        'prev_service': fields.String(example='test'),
        'failed_service': fields.String(example='test'),
        'utctime': fields.String(example='now'),
        'image': fields.String(example='test_image_oem'),
        'download_url': fields.String(
            example='http://download.opensuse.org/repositories/Cloud:Tools/images'
        ),
        'cloud_architecture': fields.String(example='x86_64'),
        'profile': fields.String(example='Server'),
        'state': fields.String(example='success'),
        'start_time': fields.DateTime(),
        'finish_time': fields.DateTime(),
        'errors': fields.List(fields.String(), skip_none=True),
        'data': fields.Nested(job_data, skip_none=True)
    }
)


@blueprint.route('/', methods=['PUT'])
def update_job_status():
    data = json.loads(request.data.decode())

    try:
        save_job_status(data)
    except Exception as error:
        msg = 'Unable to update job status: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(jsonify({'msg': 'Job status updated'}), 200)


@blueprint.route('/', methods=['POST'])
def create_job():
    data = json.loads(request.data.decode())

    try:
        job = create_new_job(data)
    except Exception as error:
        msg = 'Unable to create job: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(job, job_response, skip_none=True)),
        200
    )


@blueprint.route('/', methods=['GET'])
def get_job():
    data = json.loads(request.data.decode())
    job_id = data['job_id']
    user_id = data['user_id']

    try:
        job = get_job_by_user(job_id, user_id)
    except Exception as error:
        msg = 'Unable to get job {0} for user {1}: {2}'.format(
            job_id,
            user_id,
            error
        )
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(job, job_response, skip_none=True)),
        200
    )


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_job_list(user):
    data = json.loads(request.data.decode())
    page = data.get('page')
    per_page = data.get('per_page')

    kwargs = {}
    if page:
        kwargs['page'] = page

    if per_page:
        kwargs['per_page'] = per_page

    jobs = get_jobs(user, **kwargs)
    jobs = [marshal(job, job_response, skip_none=True) for job in jobs]
    return make_response(jsonify(jobs), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_job():
    data = json.loads(request.data.decode())
    job_id = data['job_id']
    user_id = data['user_id']

    try:
        rows_deleted = delete_job_for_user(job_id, user_id)
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Delete job failed'}),
            400
        )

    return make_response(
        jsonify({'rows_deleted': rows_deleted}),
        200
    )
