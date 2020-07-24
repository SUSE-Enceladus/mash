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

from flask import Blueprint, current_app, jsonify, request, make_response
from flask_restplus import marshal, fields, Model

from mash.services.database.utils.tokens import (
    add_user_token,
    get_token_by_jti,
    get_user_tokens,
    revoke_token_by_jti,
    revoke_user_tokens
)

blueprint = Blueprint('tokens', __name__, url_prefix='/tokens')

token_response = Model(
    'token_response', {
        'id': fields.String,
        'jti': fields.String,
        'token_type': fields.String,
        'expires': fields.DateTime
    }
)


@blueprint.route('/', methods=['POST'])
def add_token():
    data = json.loads(request.data.decode())
    jti = data['jti']
    token_type = data['token_type']
    user_id = data['user_id']
    expires = data['expires']

    try:
        add_user_token(jti, token_type, user_id, expires)
    except Exception as error:
        msg = 'Unable to add user token: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(jsonify({'msg': 'User token added.'}), 201)


@blueprint.route('/', methods=['GET'])
def get_token():
    data = json.loads(request.data.decode())
    jti = data['jti']
    user_id = data['user_id']

    token = get_token_by_jti(jti, user_id)
    return make_response(
        jsonify(marshal(token, token_response, skip_none=True)),
        200
    )


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_token_list(user):
    tokens = get_user_tokens(user)
    tokens = [
        marshal(token, token_response, skip_none=True) for token in tokens
    ]
    return make_response(jsonify(tokens), 200)


@blueprint.route('/', methods=['DELETE'])
def revoke_token():
    data = json.loads(request.data.decode())
    jti = data['jti']
    user_id = data['user_id']

    rows_deleted = revoke_token_by_jti(jti, user_id)
    return make_response(jsonify({'rows_deleted': rows_deleted}), 200)


@blueprint.route('/list/<string:user>', methods=['DELETE'])
def revoke_tokens(user):
    rows_deleted = revoke_user_tokens(user)
    return make_response(jsonify({'rows_deleted': rows_deleted}), 200)
