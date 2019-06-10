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

from flask import request
from flask_restplus import Namespace, Resource

from mash.services.api.routes.jobs import (
    job_response,
    validation_error_response,
    process_job_add_request
)
from mash.services.api.schema.jobs.ec2 import ec2_job_message

api = Namespace(
    'EC2 Jobs',
    description='EC2 Job operations'
)
ec2_job = api.schema_model('ec2_job', ec2_job_message)


@api.route('/')
@api.response(400, 'Validation error', validation_error_response)
class EC2JobCreate(Resource):
    @api.doc('add_ec2_job')
    @api.expect(ec2_job)
    @api.response(201, 'Job added', job_response)
    def post(self):
        """
        Add EC2 job.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'ec2'
        return process_job_add_request(data)
