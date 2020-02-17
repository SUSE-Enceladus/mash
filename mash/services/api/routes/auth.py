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
import jwt

from flask import jsonify, request, make_response, current_app
from flask_restplus import fields, Namespace, Resource

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_refresh_token_required,
    get_raw_jwt,
    get_jwt_identity
)

from requests_oauthlib import OAuth2Session

from mash.services.api.schema import (
    default_response,
    login_request_model,
    oauth2_request_model,
    oauth2_login_model
)
from mash.services.api.utils.tokens import (
    add_token_to_database,
    revoke_token_by_jti
)
from mash.services.api.utils.users import (
    get_user_by_username,
    verify_login,
    verify_email,
)

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
oauth2_req_request = api.schema_model(
    'oauth2_req_request', oauth2_request_model
)
oauth2_req_response = api.model(
    'oauth2_req_response', {
        'msg': fields.String,
        'auth_url': fields.String,
        'state': fields.String,
        'redirect_port': fields.Integer
    }
)
oauth2_login_request = api.schema_model(
    'oauth2_login_request', oauth2_login_model
)
oauth2_login_response = api.model(
    'oauth2_login_response', {
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
    @api.response(403, 'Forbidden', default_response)
    def post(self):
        """
        Get access and refresh tokens for new session.
        """
        data = json.loads(request.data.decode())
        username = data['username']

        if 'password' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'Password based login is disabled'}), 403)

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
            current_app.logger.warning(
                'Failed login attempt for user: {username}'.format(
                    username=username
                )
            )
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


@api.route('/oauth2_req')
class OAuth2Req(Resource):
    @api.doc('oauth2_req')
    @api.expect(oauth2_req_request)
    @api.response(200, 'Login request', oauth2_req_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(403, 'Forbidden', default_response)
    def post(self):
        """
        Request oauth2 login URL.
        """
        data = json.loads(request.data.decode())
        username = data['username']

        if 'oauth2' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'OAuth2 login is disabled'}), 403)

        if not get_user_by_username(username):
            return make_response(jsonify({'msg': 'Username is invalid'}), 401)

        oauth2_auth_url = '{}/authorize'.format(
            current_app.config['OAUTH2_PROVIDER_URL'],
        )
        oauth2_redirect_url = 'http://localhost:{}'.format(
            current_app.config['OAUTH2_REDIRECT_PORT']
        )
        oauth2_client_id = current_app.config['OAUTH2_CLIENT_ID']

        oauth2 = OAuth2Session(
            client_id=oauth2_client_id,
            redirect_uri=oauth2_redirect_url,
            scope="openid email"
        )
        auth_url, state = oauth2.authorization_url(oauth2_auth_url)
        return make_response(
            jsonify({
                'msg': 'Please open the following URL and log in',
                'auth_url': auth_url,
                'state': state,
                'redirect_port': 9000}),
            200
        )


@api.route('/oauth2_login')
class OAuth2Login(Resource):
    @api.doc('oauth2_login')
    @api.expect(oauth2_login_request)
    @api.response(200, 'Logged in', oauth2_login_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(403, 'Forbidden', default_response)
    def post(self):
        data = json.loads(request.data.decode())
        username = data['username']
        auth_code = data['auth_code']
        state = data['state']

        if 'oauth2' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'OAuth2 login is disabled'}), 403)

        oauth2_redirect_url = 'http://localhost:{}'.format(
            current_app.config['OAUTH2_REDIRECT_PORT']
        )
        oauth2_client_id = current_app.config['OAUTH2_CLIENT_ID']
        oauth2_client_secret = current_app.config['OAUTH2_CLIENT_SECRET']
        oauth2_token_url = '{}/token'.format(
            current_app.config['OAUTH2_PROVIDER_URL'],
        )

        oauth2 = OAuth2Session(
            client_id=oauth2_client_id,
            redirect_uri=oauth2_redirect_url,
            scope="openid email",
            state=state
        )
        token = oauth2.fetch_token(
            oauth2_token_url,
            client_secret=oauth2_client_secret,
            code=auth_code
        )

        # FIXME: verify signature
        user_email = jwt.decode(token['id_token'], verify=False)['email']
        if verify_email(username, user_email):
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
            current_app.logger.warning(
                'Failed login attempt for user: {username}'.format(
                    username=username
                )
            )
            return make_response(jsonify({'msg': 'Username or email is invalid'}), 401)
