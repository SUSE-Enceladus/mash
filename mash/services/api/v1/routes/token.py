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

from flask import jsonify, make_response
from flask_restx import fields, Namespace, Resource

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

from mash.services.api.v1.schema import (
    default_response
)
from mash.services.api.v1.utils.tokens import (
    add_token_to_database,
    get_user_tokens,
    get_token_by_jti,
    revoke_tokens,
    revoke_token_by_jti
)
from mash.services.database.routes.tokens import token_response

api = Namespace(
    'Token',
    description='JWT token operations'
)

refresh_response = api.model(
    'refresh_response', {
        'access_token': fields.String
    }
)

api.models['default_response'] = default_response
api.models['token_response'] = token_response


@api.route('/refresh')
class RefreshToken(Resource):
    @api.doc('refresh_token')
    @jwt_required(refresh=True)
    @api.doc(security='apiKey')
    @api.response(200, 'Success', refresh_response)
    @api.response(401, 'Unauthorized', default_response)
    @api.response(422, 'Not processable', default_response)
    def post(self):
        """
        Get new access token based on refresh token in header.
        """
        user_id = get_jwt_identity()

        access_token = create_access_token(identity=user_id)
        add_token_to_database(access_token, user_id)

        return make_response(jsonify({'access_token': access_token}), 200)


@api.route('')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class ListTokens(Resource):
    @api.doc('list_auth_tokens')
    @jwt_required()
    def get(self):
        """
        Get list of all authorization tokens.
        """
        tokens = get_user_tokens(get_jwt_identity())
        return make_response(jsonify(tokens), 200)

    @api.doc('delete_all_auth_tokens')
    @jwt_required()
    @api.response(200, 'Success', default_response)
    def delete(self):
        """
        Revoke all tokens for given identity.
        """
        rows_deleted = revoke_tokens(get_jwt_identity())
        return make_response(
            jsonify(
                {
                    'msg': 'Successfully deleted {rows} tokens'.format(
                        rows=str(rows_deleted)
                    )
                }
            ),
            200
        )


@api.route('/<string:jti>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(404, 'Not found', default_response)
@api.response(422, 'Not processable', default_response)
class Token(Resource):
    @api.doc('revoke_auth_token')
    @jwt_required()
    @api.response(200, 'Success', default_response)
    def delete(self, jti):
        """
        Revoke token based on jti.
        """
        user_id = get_jwt_identity()
        rows_deleted = revoke_token_by_jti(jti, user_id)

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'Token revoked'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'Token not found'}),
                404
            )

    @api.doc('get_auth_token')
    @jwt_required()
    @api.response(200, 'Success', token_response)
    def get(self, jti):
        """
        Get info for token based on jti.
        """
        token = get_token_by_jti(jti, get_jwt_identity())

        if token:
            return make_response(jsonify(token), 200)
        else:
            return make_response(
                jsonify({'msg': 'Token not found'}),
                404
            )
