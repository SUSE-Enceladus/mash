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
from flask_restx import marshal, fields, Model

from mash.services.database.utils.users import (
    add_new_user,
    get_user_by_id,
    get_user_by_email,
    delete_user_by_id,
    verify_login,
    reset_user_password,
    change_user_password
)

blueprint = Blueprint('users', __name__, url_prefix='/users')

user_response = Model(
    'user_response', {
        'id': fields.String,
        'email': fields.String
    }
)


@blueprint.route('/', methods=['POST'])
def add_user():
    data = json.loads(request.data.decode())

    email = data['email']
    password = data['password']
    user = add_new_user(email, password)

    return make_response(
        jsonify(marshal(user, user_response, skip_none=True)),
        201
    )


@blueprint.route('/<string:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_by_id(user_id)
    return make_response(
        jsonify(marshal(user, user_response, skip_none=True)),
        200
    )


@blueprint.route('/get_user/<string:email>', methods=['GET'])
def get_or_create_user(email):
    data = json.loads(request.data.decode())
    create = data['create']

    user = get_user_by_email(email, create)
    return make_response(
        jsonify(marshal(user, user_response, skip_none=True)),
        200
    )


@blueprint.route('/login/', methods=['POST'])
def validate_login():
    data = json.loads(request.data.decode())
    email = data['email']
    password = data['password']

    try:
        user = verify_login(email, password)
    except Exception as error:
        return make_response(jsonify({'msg': str(error)}), 403)

    return make_response(
        jsonify(marshal(user, user_response, skip_none=True)),
        200
    )


@blueprint.route('/<string:user_id>', methods=['DELETE'])
def delete_user(user_id):
    status = delete_user_by_id(user_id)

    if status:
        return make_response(jsonify({'msg': 'User deleted.'}), 200)
    else:
        msg = 'Unable to delete user: {0}'.format(user_id)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 404)


@blueprint.route('/password/reset/<string:email>', methods=['POST'])
def password_reset(email):
    temp_password = reset_user_password(email)

    if temp_password:
        return make_response(jsonify({'password': temp_password}), 200)
    else:
        msg = 'Unable to reset user password for {0}'.format(email)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 404)


@blueprint.route('/password/change/<string:email>', methods=['POST'])
def change_password(email):
    data = json.loads(request.data.decode())
    current_password = data['current_password']
    new_password = data['new_password']
    status = change_user_password(email, current_password, new_password)

    if status:
        return make_response(jsonify({'msg': 'Password changed'}), 200)
    else:
        msg = 'Unable to change user password for {0}'.format(email)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 403)
