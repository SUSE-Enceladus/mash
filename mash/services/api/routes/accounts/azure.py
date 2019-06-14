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
from mash.services.api.schema.accounts.azure import add_account_azure
from mash.services.api.routes.utils import publish

api = Namespace(
    'Azure Accounts',
    description='Azure account related operations'
)
azure_account = api.schema_model('azure_account', add_account_azure)


@api.route('/')
@api.response(400, 'Validation error', validation_error_response)
class AzureAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for Azure.

    TODO: List accounts (GET) endpoint will be implemented in the future.
    """

    @api.doc('create_azure_account')
    @api.expect(azure_account)
    @api.response(201, 'Azure account created', account_response)
    def post(self):
        """
        Create a new Azure account.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'azure'

        publish(
            'jobcreator', 'add_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': data['account_name']}), 201)


@api.route('/<int:id>')
@api.response(400, 'Validation error', validation_error_response)
class AzureAccount(Resource):
    @api.doc('delete_azure_account')
    @api.expect(delete_account_request)
    @api.response(200, 'Azure account deleted', account_response)
    def delete(self, id):
        """
        Delete Azure account matching id.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'azure'

        publish(
            'jobcreator', 'delete_account', json.dumps(data, sort_keys=True)
        )
        return make_response(jsonify({'name': data['account_name']}), 200)
