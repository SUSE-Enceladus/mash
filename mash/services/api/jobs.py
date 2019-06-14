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

from flask import jsonify, make_response
from flask_restplus import fields, Namespace, Resource

from mash.services.api.schema import validation_error
from mash.services.api.utils import publish

api = Namespace(
    'Jobs',
    description='Job related operations'
)

job_response = api.model(
    'job_response', {
        'job_id': fields.String
    }
)
validation_error_response = api.schema_model(
    'validation_error',
    validation_error
)


def process_job_add_request(data):
    job_id = str(uuid.uuid4())
    data['job_id'] = job_id

    publish(
        'jobcreator', 'job_document', json.dumps(data, sort_keys=True)
    )

    # Cannot use jsonify with multiple keys, need sorted dump for py3.4
    response = make_response(
        json.dumps(
            {'job_id': job_id},
            sort_keys=True
        ),
        201
    )
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    return response


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
