# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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
    add_account,
    default_response,
    validation_error,
    password_change,
    password_reset
)
from mash.services.api.v1.utils.users import (
    add_user,
    get_user_by_id,
    delete_user,
    reset_user_password,
    change_user_password
)
from mash.services.database.routes.users import user_response

api = Namespace(
    'User',
    description='User operations'
)
add_account_request = api.schema_model(
    'add_account_request', add_account
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)
password_reset_request = api.schema_model(
    'password_reset_request', password_reset
)
password_change_request = api.schema_model(
    'password_change_request', password_change
)

api.models['user_response'] = user_response
api.models['default_response'] = default_response


@api.route('/')
class Account(Resource):
    @api.doc('create_mash_account')
    @api.expect(add_account_request)
    @api.response(201, 'Created account', user_response)
    @api.response(400, 'Validation error', default_response)
    @api.response(403, 'Forbidden', default_response)
    @api.response(409, 'Already in use', default_response)
    def post(self):
        """
        Create a new MASH account.
        """
        if 'password' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'Password based login is disabled'}), 403)

        data = json.loads(request.data.decode())

        try:
            user = add_user(data['email'], data['password'])
        except Exception as error:
            return make_response(
                jsonify({"msg": str(error)}),
                400
            )

        if user:
            return make_response(jsonify(user), 201)
        else:
            return make_response(
                jsonify({'msg': 'Email already in use'}),
                409
            )

    @api.doc('get_mash_account')
    @api.doc(security='apiKey')
    @jwt_required()
    @api.response(200, 'Account', user_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(422, 'Not processable', default_response)
    def get(self):
        """
        Returns MASH account.
        """
        user = get_user_by_id(get_jwt_identity())
        return make_response(jsonify(user), 200)

    @api.doc('delete_mash_account')
    @api.doc(security='apiKey')
    @jwt_required()
    @api.response(200, 'Account deleted', default_response)
    @api.response(400, 'Delete account failed', default_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(422, 'Not processable', default_response)
    def delete(self):
        """
        Delete MASH account.
        """
        rows_deleted = delete_user(get_jwt_identity())

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Delete account failed'}),
                400
            )


@api.route('/password')
class UserPassword(Resource):
    @api.doc('password_reset')
    @api.expect(password_reset_request)
    @api.response(200, 'Initiated Password Reset', default_response)
    def post(self):
        """
        Initiate password reset.
        """
        data = json.loads(request.data.decode())

        try:
            reset_user_password(data['email'])
        except Exception:
            return make_response(
                jsonify({'msg': 'Password reset failed.'}),
                404
            )

        return make_response(
            jsonify({
                'msg': 'Password reset submitted. An email '
                       'will be sent with steps to change your password.'
            }),
            200
        )

    @api.doc('password_change')
    @api.expect(password_change_request)
    @api.response(200, 'Password Changed', default_response)
    def put(self):
        """
        Change password.
        """
        data = json.loads(request.data.decode())

        try:
            change_user_password(
                data['email'],
                data['current_password'],
                data['new_password']
            )
        except Exception as error:
            return make_response(
                jsonify({'msg': str(error)}),
                404
            )

        return make_response(
            jsonify({
                'msg': 'Password changed successfully. You can now login.'
            }),
            200
        )
