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

from flask import Blueprint, current_app, jsonify, request, make_response
from flask_restplus import marshal, fields, Model
from sqlalchemy.exc import IntegrityError

from mash.services.database.utils.accounts.aliyun import (
    create_new_aliyun_account,
    get_aliyun_accounts,
    get_aliyun_account_for_user,
    delete_aliyun_account_for_user,
    update_aliyun_account_for_user
)

blueprint = Blueprint('aliyun_accounts', __name__, url_prefix='/aliyun_accounts')

aliyun_account_response = Model(
    'aliyun_account_response', {
        'id': fields.String,
        'name': fields.String,
        'bucket': fields.String,
        'region': fields.String,
        'security_group_id': fields.String,
        'vswitch_id': fields.String
    }
)


@blueprint.route('/', methods=['POST'])
def create_aliyun_account():
    data = json.loads(request.data.decode())

    try:
        account = create_new_aliyun_account(
            data['user_id'],
            data['account_name'],
            data['bucket'],
            data['region'],
            data['credentials'],
            data.get('security_group_id'),
            data.get('vswitch_id')
        )
    except IntegrityError:
        return make_response(
            jsonify({'msg': 'Account already exists'}),
            400
        )
    except Exception as error:
        msg = 'Unable to create Aliyun account: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(account, aliyun_account_response, skip_none=True)),
        201
    )


@blueprint.route('/', methods=['GET'])
def get_aliyun_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    account = get_aliyun_account_for_user(name, user_id)
    return make_response(
        jsonify(marshal(account, aliyun_account_response, skip_none=True)),
        200
    )


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_aliyun_account_list(user):
    accounts = get_aliyun_accounts(user)
    accounts = [marshal(account, aliyun_account_response, skip_none=True) for account in accounts]
    return make_response(jsonify(accounts), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_aliyun_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    try:
        rows_deleted = delete_aliyun_account_for_user(name, user_id)
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Delete Aliyun account failed'}),
            400
        )

    return make_response(
        jsonify({'rows_deleted': rows_deleted}),
        200
    )


@blueprint.route('/', methods=['PUT'])
def update_aliyun_account():
    data = json.loads(request.data.decode())

    try:
        account = update_aliyun_account_for_user(
            data['account_name'],
            data['user_id'],
            data.get('bucket'),
            data.get('region'),
            data.get('credentials'),
            data.get('security_group_id'),
            data.get('vswitch_id')
        )
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Update Aliyun account failed'}),
            400
        )

    return make_response(
        jsonify(marshal(account, aliyun_account_response, skip_none=True)),
        200
    )
