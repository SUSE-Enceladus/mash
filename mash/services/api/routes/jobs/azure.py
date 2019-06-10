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
from mash.services.api.schema.jobs.azure import azure_job_message

api = Namespace(
    'Azure Jobs',
    description='Azure Job operations'
)
azure_job = api.schema_model('azure_job', azure_job_message)


@api.route('/')
@api.response(400, 'Validation error', validation_error_response)
class AzureJobCreate(Resource):
    @api.doc('add_azure_job')
    @api.expect(azure_job)
    @api.response(201, 'Job added', job_response)
    def post(self):
        """
        Add Azure job.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'azure'
        return process_job_add_request(data)
