# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from mash.services.api.v1.schema import (
    default_response,
    validation_error
)
from mash.services.api.v1.schema.accounts.aliyun import (
    add_account_aliyun,
    aliyun_account_update
)
from mash.services.api.v1.utils.accounts.aliyun import (
    create_aliyun_account,
    get_aliyun_account,
    get_aliyun_accounts,
    delete_aliyun_account,
    update_aliyun_account
)
from mash.services.database.routes.accounts.aliyun import aliyun_account_response

api = Namespace(
    'Aliyun Accounts',
    description='Aliyun account operations'
)
add_aliyun_account_request = api.schema_model('aliyun_account', add_account_aliyun)
update_aliyun_account_request = api.schema_model(
    'aliyun_account_update',
    aliyun_account_update
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)

api.models['aliyun_account_response'] = aliyun_account_response


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class AliyunAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for Aliyun.
    """

    @api.doc('create_aliyun_account')
    @jwt_required()
    @api.expect(add_aliyun_account_request)
    @api.response(201, 'Aliyun account created', aliyun_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(409, 'Duplicate account', default_response)
    def post(self):
        """
        Create a new Aliyun account.
        """
        data = json.loads(request.data.decode())

        try:
            account = create_aliyun_account(
                get_jwt_identity(),
                data
            )
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        return make_response(jsonify(account), 201)

    @api.doc('get_aliyun_accounts')
    @jwt_required()
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all Aliyun accounts.
        """
        aliyun_accounts = get_aliyun_accounts(get_jwt_identity())
        return aliyun_accounts


@api.route('/<string:name>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class AliyunAccount(Resource):
    @api.doc('delete_aliyun_account')
    @jwt_required()
    @api.response(200, 'Aliyun account deleted', default_response)
    @api.response(400, 'Delete Aliyun account failed', default_response)
    @api.response(404, 'Not found', default_response)
    def delete(self, name):
        """
        Delete Aliyun account matching name for requesting user.
        """
        try:
            rows_deleted = delete_aliyun_account(name, get_jwt_identity())
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': 'Delete Aliyun account failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Aliyun account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Aliyun account not found'}),
                404
            )

    @api.doc('get_aliyun_account')
    @jwt_required()
    @api.response(200, 'Success', aliyun_account_response)
    @api.response(404, 'Not found', default_response)
    def get(self, name):
        """
        Get Aliyun account.
        """
        try:
            account = get_aliyun_account(name, get_jwt_identity())
        except Exception:
            account = None

        if account:
            return make_response(jsonify(account), 200)
        else:
            return make_response(
                jsonify({'msg': 'Aliyun account not found'}),
                404
            )

    @api.doc('update_aliyun_account')
    @jwt_required()
    @api.expect(update_aliyun_account_request)
    @api.response(200, 'Success', aliyun_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(404, 'Not found', default_response)
    def post(self, name):
        """
        Update Aliyun account.
        """
        data = json.loads(request.data.decode())

        try:
            account = update_aliyun_account(
                name,
                get_jwt_identity(),
                data
            )
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        if account:
            return make_response(jsonify(account), 200)
        else:
            return make_response(
                jsonify({'msg': 'Aliyun account not found'}),
                404
            )
