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
from flask_restplus import fields, Namespace, Resource

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_refresh_token_required,
    get_raw_jwt,
    get_jwt_identity
)

from mash.services.api.schema import (
    default_response,
    login_request_model
)
from mash.services.api.utils.tokens import (
    add_token_to_database,
    revoke_token_by_jti
)
from mash.services.api.utils.users import verify_login

api = Namespace(
    'Auth',
    description='Authentication operations'
)

login_request = api.schema_model(
    'login_request', login_request_model
)
login_response = api.model(
    'login_response', {
        'access_token': fields.String,
        'refresh_token': fields.String
    }
)

api.models['default_response'] = default_response


@api.route('/login')
class Login(Resource):
    @api.doc('account_logout')
    @api.expect(login_request)
    @api.response(200, 'Logged in', login_response)
    @api.response(401, 'Unauthorized', default_response)
    def post(self):
        """
        Get access and refresh tokens for new session.
        """
        data = json.loads(request.data.decode())
        username = data['username']

        if verify_login(username, data['password']):
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)

            add_token_to_database(access_token, username)
            add_token_to_database(refresh_token, username)

            response = {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            return make_response(jsonify(response), 200)
        else:
            return make_response(jsonify({'msg': 'Username or password is invalid'}), 401)


@api.route('/logout')
class Logout(Resource):
    @api.doc('account_login')
    @jwt_refresh_token_required
    @api.doc(security='apiKey')
    @api.response(200, 'Logged out', default_response)
    @api.response(400, 'Logout failed', default_response)
    @api.response(422, 'Not processable', default_response)
    def delete(self):
        """
        Revoke current refresh token.
        """
        username = get_jwt_identity()
        token = get_raw_jwt()
        rows_deleted = revoke_token_by_jti(token['jti'], username)

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Successfully logged out'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Logout failed'}),
                400
            )
