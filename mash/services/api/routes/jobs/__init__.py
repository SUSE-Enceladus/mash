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

from flask import jsonify, make_response
from flask_restplus import fields, Namespace, Resource

from mash.services.api.schema import validation_error
from mash.services.api.utils.amqp import publish

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
    'validation_error',
    validation_error
)


@api.route('/<string:job_id>')
@api.response(400, 'Validation error', validation_error_response)
class Job(Resource):
    @api.doc('delete_job')
    @api.response(200, 'Job deleted', job_response)
    def delete(self, job_id):
        """
        Delete job matching job_id.
        """
        content = {'job_delete': job_id}
        publish('jobcreator', 'job_document', json.dumps(content, sort_keys=True))
        return make_response(jsonify({'job_id': job_id}), 200)
