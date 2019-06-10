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
from mash.services.api.schema.accounts.ec2 import add_account_ec2
from mash.services.api.routes.utils import publish

api = Namespace(
    'EC2 Accounts',
    description='EC2 account operations'
)
ec2_account = api.schema_model('ec2_account', add_account_ec2)


@api.route('/')
@api.response(400, 'Validation error', validation_error_response)
class EC2AccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for EC2.

    TODO: List accounts (GET) endpoint will be implemented in the future.
    """

    @api.doc('create_ec2_account')
    @api.expect(ec2_account)
    @api.response(201, 'EC2 account created', account_response)
    def post(self):
        """
        Create a new EC2 account.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'ec2'

        publish(
            'jobcreator', 'add_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': data['account_name']}), 201)


@api.route('/<string:name>')
@api.response(400, 'Validation error', validation_error_response)
class EC2Account(Resource):
    @api.doc('delete_ec2_account')
    @api.expect(delete_account_request)
    @api.response(200, 'EC2 account deleted', account_response)
    def delete(self, name):
        """
        Delete EC2 account matching name for requesting user.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'ec2'

        publish(
            'jobcreator', 'delete_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': name}), 200)
