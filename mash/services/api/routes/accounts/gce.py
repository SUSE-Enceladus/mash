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

from flask import jsonify, request, make_response
from flask_restplus import Namespace, Resource

from mash.services.api.routes.accounts import (
    account_response,
    validation_error_response,
    delete_account_request
)
from mash.services.api.schema.accounts.gce import add_account_gce
from mash.services.api.routes.amqp_utils import publish

api = Namespace(
    'GCE Accounts',
    description='GCE account operations'
)
gce_account = api.schema_model('gce_account', add_account_gce)


@api.route('/')
@api.response(400, 'Validation error', validation_error_response)
class GCEAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for GCE.

    TODO: List accounts (GET) endpoint will be implemented in the future.
    """

    @api.doc('create_gce_account')
    @api.expect(gce_account)
    @api.response(201, 'GCE account created', account_response)
    def post(self):
        """
        Create a new GCE account.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'gce'

        publish(
            'jobcreator', 'add_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': data['account_name']}), 201)


@api.route('/<string:name>')
@api.response(400, 'Validation error', validation_error_response)
class GCEAccount(Resource):
    @api.doc('delete_gce_account')
    @api.expect(delete_account_request)
    @api.response(200, 'GCE account deleted', account_response)
    def delete(self, name):
        """
        Delete GCE account matching name for requesting user.
        """
        data = json.loads(request.data.decode())
        data['account_name'] = name
        data['cloud'] = 'gce'

        publish(
            'jobcreator', 'delete_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': name}), 200)
