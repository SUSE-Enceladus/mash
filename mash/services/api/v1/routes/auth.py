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
from flask_restx import fields, Namespace, Resource

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity
)

from requests_oauthlib import OAuth2Session

from mash.services.api.v1.schema import (
    default_response,
    login_request_model,
    oauth2_login_model
)
from mash.services.api.v1.utils.tokens import (
    add_token_to_database,
    revoke_token_by_jti
)
from mash.services.api.v1.utils.users import (
    verify_login,
    email_in_whitelist,
    get_user_by_email
)
from mash.services.api.v1.utils.jwt import decode_token

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
        if 'password' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'Password based login is disabled'}), 403)

        data = json.loads(request.data.decode())
        email = data['email']

        try:
            user = verify_login(email, data['password'])
        except Exception as error:
            return make_response(
                jsonify({'msg': str(error)}),
                403
            )

        if user:
            access_token = create_access_token(identity=user['id'])
            refresh_token = create_refresh_token(identity=user['id'])

            add_token_to_database(access_token, user['id'])
            add_token_to_database(refresh_token, user['id'])

            response = {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            return make_response(jsonify(response), 200)
        else:
            current_app.logger.warning(
                'Failed login attempt for user: {email}'.format(
                    email=email
                )
            )
            return make_response(jsonify({'msg': 'Email or password is invalid'}), 401)


@api.route('/logout')
class Logout(Resource):
    @api.doc('account_login')
    @jwt_required(refresh=True)
    @api.doc(security='apiKey')
    @api.response(200, 'Logged out', default_response)
    @api.response(400, 'Logout failed', default_response)
    @api.response(422, 'Not processable', default_response)
    def delete(self):
        """
        Revoke current refresh token.
        """
        user_id = get_jwt_identity()
        token = get_jwt()
        rows_deleted = revoke_token_by_jti(token['jti'], user_id)

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


@api.route('/oauth2')
@api.doc('oauth2')
@api.response(401, 'Unauthorized', default_response)
@api.response(403, 'Forbidden', default_response)
class OAuth2Request(Resource):
    @api.response(200, 'Login request', oauth2_req_response)
    def get(self):
        """
        Request oauth2 login URL.
        """
        if 'oauth2' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'OAuth2 login is disabled'}), 403)

        oauth2_auth_url = '{}/authorize'.format(
            current_app.config['OAUTH2_PROVIDER_URL'],
        )
        oauth2_client_id = current_app.config['OAUTH2_CLIENT_ID']
        oauth2_redirect_ports = current_app.config['OAUTH2_REDIRECT_PORTS']

        oauth2 = OAuth2Session(
            client_id=oauth2_client_id,
            scope="openid email"
        )
        auth_url, state = oauth2.authorization_url(oauth2_auth_url)
        return make_response(
            jsonify({
                'msg': 'Please open the following URL and log in',
                'auth_url': auth_url,
                'state': state,
                'redirect_ports': oauth2_redirect_ports}),
            200
        )

    @api.expect(oauth2_login_request)
    @api.response(200, 'Logged in', oauth2_login_response)
    @api.response(500, 'Login failed', default_response)
    def post(self):
        if 'oauth2' not in current_app.config['AUTH_METHODS']:
            return make_response(jsonify({'msg': 'OAuth2 login is disabled'}), 403)

        data = json.loads(request.data.decode())
        auth_code = data['auth_code']
        state = data['state']
        redirect_port = data['redirect_port']

        oauth2_redirect_uri = 'http://localhost:{}'.format(redirect_port)
        oauth2_client_id = current_app.config['OAUTH2_CLIENT_ID']
        oauth2_client_secret = current_app.config['OAUTH2_CLIENT_SECRET']
        oauth2_token_url = '{}/token'.format(
            current_app.config['OAUTH2_PROVIDER_URL'],
        )

        oauth2 = OAuth2Session(
            client_id=oauth2_client_id,
            redirect_uri=oauth2_redirect_uri,
            scope="openid email",
            state=state
        )
        token = oauth2.fetch_token(
            oauth2_token_url,
            client_secret=oauth2_client_secret,
            code=auth_code
        )

        try:
            user_email = decode_token(
                current_app.config['OAUTH2_PROVIDER_URL'],
                token['id_token'],
                audience=current_app.config['OAUTH2_CLIENT_ID']
            )['email']
        except Exception as e:
            msg = 'ERROR decoding JWT: {}'.format(str(e))
            current_app.logger.warning(msg)
            return make_response(
                jsonify({'msg': 'Login failed ({})'.format(msg)}),
                500
            )

        if email_in_whitelist(user_email):
            user = get_user_by_email(user_email, create=True)
            access_token = create_access_token(identity=user['id'])
            refresh_token = create_refresh_token(identity=user['id'])

            add_token_to_database(access_token, user['id'])
            add_token_to_database(refresh_token, user['id'])

            response = {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            return make_response(jsonify(response), 200)
        else:
            current_app.logger.warning(
                'Failed login attempt for user: {email}'.format(
                    email=user_email
                )
            )
            return make_response(jsonify({'msg': 'Email is invalid'}), 401)
