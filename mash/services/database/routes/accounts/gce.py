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
from sqlalchemy.exc import IntegrityError

from mash.services.database.utils.accounts.gce import (
    create_new_gce_account,
    get_gce_accounts,
    get_gce_account_for_user,
    delete_gce_account_for_user,
    update_gce_account_for_user
)

blueprint = Blueprint('gce_accounts', __name__, url_prefix='/gce_accounts')

gce_account_response = Model(
    'gce_account_response', {
        'id': fields.String,
        'name': fields.String,
        'bucket': fields.String,
        'region': fields.String,
        'testing_account': fields.String,
        'is_publishing_account': fields.Boolean
    }
)


@blueprint.route('/', methods=['POST'])
def create_gce_account():
    data = json.loads(request.data.decode())

    try:
        account = create_new_gce_account(
            data['user_id'],
            data['account_name'],
            data['bucket'],
            data['region'],
            data['credentials'],
            data.get('testing_account'),
            data.get('is_publishing_account', False)
        )
    except IntegrityError:
        return make_response(
            jsonify({'msg': 'Account already exists'}),
            400
        )
    except Exception as error:
        msg = 'Unable to create GCE account: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(account, gce_account_response, skip_none=True)),
        201
    )


@blueprint.route('/', methods=['GET'])
def get_gce_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    account = get_gce_account_for_user(name, user_id)
    return make_response(
        jsonify(marshal(account, gce_account_response, skip_none=True)),
        200
    )


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_gce_account_list(user):
    accounts = get_gce_accounts(user)
    accounts = [marshal(account, gce_account_response, skip_none=True) for account in accounts]
    return make_response(jsonify(accounts), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_gce_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    try:
        rows_deleted = delete_gce_account_for_user(name, user_id)
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Delete GCE account failed'}),
            400
        )

    return make_response(
        jsonify({'rows_deleted': rows_deleted}),
        200
    )


@blueprint.route('/', methods=['PUT'])
def update_gce_account():
    data = json.loads(request.data.decode())

    try:
        account = update_gce_account_for_user(
            data['account_name'],
            data['user_id'],
            data.get('bucket'),
            data.get('region'),
            data.get('credentials'),
            data.get('testing_account')
        )
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Update GCE account failed'}),
            400
        )

    return make_response(
        jsonify(marshal(account, gce_account_response, skip_none=True)),
        200
    )
