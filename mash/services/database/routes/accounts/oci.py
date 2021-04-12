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

from mash.services.database.utils.accounts.oci import (
    create_new_oci_account,
    get_oci_accounts,
    get_oci_account_for_user,
    delete_oci_account_for_user,
    update_oci_account_for_user
)

blueprint = Blueprint('oci_accounts', __name__, url_prefix='/oci_accounts')

oci_account_response = Model(
    'oci_account_response', {
        'id': fields.String,
        'name': fields.String,
        'bucket': fields.String,
        'region': fields.String,
        'availability_domain': fields.String,
        'compartment_id': fields.String,
        'oci_user_id': fields.String,
        'tenancy': fields.String
    }
)


@blueprint.route('/', methods=['POST'])
def create_oci_account():
    data = json.loads(request.data.decode())

    try:
        account = create_new_oci_account(
            data['user_id'],
            data['account_name'],
            data['bucket'],
            data['region'],
            data['availability_domain'],
            data['compartment_id'],
            data['oci_user_id'],
            data['tenancy'],
            data['signing_key']
        )
    except IntegrityError:
        return make_response(
            jsonify({'msg': 'Account already exists'}),
            400
        )
    except Exception as error:
        msg = 'Unable to create OCI account: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(account, oci_account_response, skip_none=True)),
        201
    )


@blueprint.route('/', methods=['GET'])
def get_oci_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    account = get_oci_account_for_user(name, user_id)
    return make_response(
        jsonify(marshal(account, oci_account_response, skip_none=True)),
        200
    )


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_oci_account_list(user):
    accounts = get_oci_accounts(user)
    accounts = [marshal(account, oci_account_response, skip_none=True) for account in accounts]
    return make_response(jsonify(accounts), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_oci_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    try:
        rows_deleted = delete_oci_account_for_user(name, user_id)
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Delete OCI account failed'}),
            400
        )

    return make_response(
        jsonify({'rows_deleted': rows_deleted}),
        200
    )


@blueprint.route('/', methods=['PUT'])
def update_oci_account():
    data = json.loads(request.data.decode())

    try:
        account = update_oci_account_for_user(
            data['account_name'],
            data['user_id'],
            data.get('bucket'),
            data.get('region'),
            data.get('availability_domain'),
            data.get('compartment_id'),
            data.get('oci_user_id'),
            data.get('tenancy'),
            data.get('signing_key')
        )
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Update OCI account failed'}),
            400
        )

    return make_response(
        jsonify(marshal(account, oci_account_response, skip_none=True)),
        200
    )
