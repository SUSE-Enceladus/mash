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
from flask_restplus import fields, marshal, Model, Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)
from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashException
from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.schema.accounts.azure import (
    add_account_azure,
    azure_account_update
)
from mash.services.api.utils.accounts.azure import (
    create_azure_account,
    get_azure_account,
    get_azure_accounts,
    delete_azure_account,
    update_azure_account
)

api = Namespace(
    'Azure Accounts',
    description='azure account operations'
)
add_azure_account_request = api.schema_model('azure_account', add_account_azure)
update_azure_account_request = api.schema_model(
    'azure_account_update',
    azure_account_update
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)

azure_account_response = Model(
    'azure_account_response', {
        'id': fields.String,
        'name': fields.String,
        'region': fields.String,
        'source_container': fields.String,
        'source_resource_group': fields.String,
        'source_storage_account': fields.String,
        'destination_container': fields.String,
        'destination_resource_group': fields.String,
        'destination_storage_account': fields.String
    }
)

api.models['azure_account_response'] = azure_account_response


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class AzureAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for Azure.
    """

    @api.doc('create_azure_account')
    @jwt_required
    @api.expect(add_azure_account_request)
    @api.response(201, 'Azure account created', azure_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(409, 'Duplicate account', default_response)
    def post(self):
        """
        Create a new Azure account.
        """
        data = json.loads(request.data.decode())

        try:
            account = create_azure_account(
                get_jwt_identity(),
                data['account_name'],
                data['region'],
                data['credentials'],
                data['source_container'],
                data['source_resource_group'],
                data['source_storage_account'],
                data['destination_container'],
                data['destination_resource_group'],
                data['destination_storage_account']
            )
        except MashException as error:
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )
        except IntegrityError:
            return make_response(
                jsonify({'msg': 'Account already exists'}),
                409
            )
        except Exception:
            return make_response(
                jsonify({'msg': 'Failed to add Azure account'}),
                400
            )

        return make_response(
            jsonify(marshal(account, azure_account_response, skip_none=True)),
            201
        )

    @api.doc('get_azure_accounts')
    @jwt_required
    @api.marshal_list_with(azure_account_response, skip_none=True)
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all Azure accounts.
        """
        azure_accounts = get_azure_accounts(get_jwt_identity())
        return azure_accounts


@api.route('/<string:name>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class AzureAccount(Resource):
    @api.doc('delete_azure_account')
    @jwt_required
    @api.response(200, 'Azure account deleted', default_response)
    @api.response(400, 'Delete Azure account failed', default_response)
    @api.response(404, 'Not found', default_response)
    def delete(self, name):
        """
        Delete Azure account matching name for requesting user.
        """
        try:
            rows_deleted = delete_azure_account(name, get_jwt_identity())
        except Exception:
            return make_response(
                jsonify({'msg': 'Delete Azure account failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Azure account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Azure account not found'}),
                404
            )

    @api.doc('get_azure_account')
    @jwt_required
    @api.response(200, 'Success', azure_account_response)
    @api.response(404, 'Not found', default_response)
    def get(self, name):
        """
        Get Azure account.
        """
        account = get_azure_account(name, get_jwt_identity())

        if account:
            return make_response(
                jsonify(marshal(account, azure_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Azure account not found'}),
                404
            )

    @api.doc('update_azure_account')
    @jwt_required
    @api.expect(update_azure_account_request)
    @api.response(200, 'Azure account updated', azure_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(404, 'Not found', default_response)
    def post(self, name):
        """
        Update an Azure account.
        """
        data = json.loads(request.data.decode())

        try:
            account = update_azure_account(
                name,
                get_jwt_identity(),
                data.get('region'),
                data.get('credentials'),
                data.get('source_container'),
                data.get('source_resource_group'),
                data.get('source_storage_account'),
                data.get('destination_container'),
                data.get('destination_resource_group'),
                data.get('destination_storage_account')
            )
        except Exception as error:
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        if account:
            return make_response(
                jsonify(marshal(account, azure_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Azure account not found'}),
                404
            )
