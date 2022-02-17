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

from flask import jsonify, request, make_response, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)

from mash.mash_exceptions import MashException
from mash.services.api.v1.schema import (
    default_response,
    validation_error
)
from mash.services.api.v1.routes.jobs import job_response

from mash.services.api.v1.schema.jobs.ec2 import ec2_job_message
from mash.services.api.v1.utils.jobs.ec2 import validate_ec2_job
from mash.services.api.v1.utils.jobs import create_job

api = Namespace(
    'EC2 Jobs',
    description='EC2 Job operations'
)
ec2_job = api.schema_model('ec2_job', ec2_job_message)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)


@api.route('/')
class EC2JobCreate(Resource):
    @api.doc('add_ec2_job', security='apiKey')
    @jwt_required()
    @api.expect(ec2_job)
    @api.response(201, 'Job added', job_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(422, 'Not processable', default_response)
    def post(self):
        """
        Add EC2 job.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'ec2'
        data['requesting_user'] = get_jwt_identity()

        try:
            data = validate_ec2_job(data)
            job = create_job(data)
        except MashException as error:
            return make_response(
                jsonify({'msg': 'Job failed: {0}'.format(error)}),
                400
            )
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': 'Failed to start job'}),
                400
            )

        if job:
            return make_response(
                jsonify(job),
                201
            )
        else:
            return make_response(
                jsonify({'msg': 'Job doc is valid!'}),
                200
            )

    @api.doc('get_ec2_job_doc_schema')
    @api.response(200, 'Success', ec2_job)
    def get(self):
        """
        Get ec2 job doc schema.
        """
        return make_response(jsonify(ec2_job_message), 200)
