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

from flask import jsonify, make_response, current_app
from flask_restplus import marshal, fields, Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.utils.jobs import delete_job, get_job, get_jobs


api = Namespace(
    'Jobs',
    description='Job operations'
)

job_response = api.model(
    'job_response', {
        'job_id': fields.String(
            example='12345678-1234-1234-1234-123456789012'
        ),
        'last_service': fields.String(example='testing'),
        'utctime': fields.String(example='now'),
        'image': fields.String(example='test_image_oem'),
        'download_url': fields.String(
            example='http://download.opensuse.org/repositories/Cloud:Tools/images'
        ),
        'cloud_architecture': fields.String(example='x86_64'),
        'profile': fields.String(example='Server')
    }
)
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
    @api.marshal_list_with(job_response, skip_none=True)
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all jobs.
        """
        jobs = get_jobs(get_jwt_identity())
        return jobs


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
                jsonify({'msg': 'Delete job failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Job deleted'}),
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
        account = get_job(job_id, get_jwt_identity())

        if account:
            return make_response(
                jsonify(marshal(account, job_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Job not found'}),
                404
            )
