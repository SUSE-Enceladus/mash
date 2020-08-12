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

from flask import jsonify, make_response, current_app
from flask_restplus import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.utils.jobs import delete_job, get_job, get_jobs
from mash.services.database.routes.jobs import job_response, job_data


api = Namespace(
    'Jobs',
    description='Job operations'
)

api.models['job_data'] = job_data
api.models['job_response'] = job_response

validation_error_response = api.schema_model(
    'validation_error', validation_error
)


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class JobList(Resource):
    """
    Handles list jobs.
    """

    @api.doc('get_jobs')
    @jwt_required
    @api.response(200, 'Success', job_response)
    def get(self):
        """
        Get all jobs.
        """
        jobs = get_jobs(get_jwt_identity())
        return make_response(jsonify(jobs), 200)


@api.route('/<string:job_id>')
@api.doc(security='apiKey')
@api.response(400, 'Validation error', validation_error_response)
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class Job(Resource):
    @api.doc('delete_job')
    @jwt_required
    @api.response(200, 'Job deleted', default_response)
    def delete(self, job_id):
        """
        Delete job matching job_id.
        """
        try:
            rows_deleted = delete_job(job_id, get_jwt_identity())
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Job deletion request submitted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Job not found'}),
                404
            )

    @api.doc('get_job')
    @jwt_required
    @api.response(200, 'Success', job_response)
    @api.response(404, 'Not found', default_response)
    def get(self, job_id):
        """
        Get job.
        """
        job = get_job(job_id, get_jwt_identity())

        if job:
            return make_response(jsonify(job), 200)
        else:
            return make_response(jsonify({'msg': 'Job not found'}), 404)
