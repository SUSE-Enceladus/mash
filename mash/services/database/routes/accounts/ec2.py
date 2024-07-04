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

from mash.services.database.utils.accounts.ec2 import (
    create_new_ec2_account,
    get_ec2_accounts,
    get_ec2_account_for_user,
    delete_ec2_account_for_user,
    update_ec2_account_for_user,
    get_accounts_in_ec2_group
)

blueprint = Blueprint('ec2_accounts', __name__, url_prefix='/ec2_accounts')

region = Model(
    'region', {
        'id': fields.String,
        'name': fields.String,
        'helper_image': fields.String
    }
)

ec2_test_region = Model(
    'ec2_test_region', {
        'region': fields.String,
        'subnet': fields.String
    }
)

group = Model(
    'group', {
        'id': fields.String,
        'name': fields.String
    }
)

ec2_account_response = Model(
    'ec2_account_response', {
        'id': fields.String,
        'name': fields.String,
        'partition': fields.String,
        'region': fields.String,
        'subnet': fields.String,
        'additional_regions': fields.List(
            fields.Nested(region, skip_none=True)
        ),
        'group': fields.Nested(group, skip_none=True),
        'test_regions': fields.List(
            fields.Nested(ec2_test_region, skip_none=True)
        ),

    }
)


@blueprint.route('/', methods=['POST'])
def create_ec2_account():
    data = json.loads(request.data.decode())

    try:
        account = create_new_ec2_account(
            data['user_id'],
            data['account_name'],
            data['partition'],
            data['region'],
            data['credentials'],
            data.get('subnet'),
            data.get('group'),
            data.get('additional_regions'),
            data.get('test_regions')
        )
    except IntegrityError:
        return make_response(
            jsonify({'msg': 'Account already exists'}),
            400
        )
    except Exception as error:
        msg = 'Unable to create EC2 account: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(
        jsonify(marshal(account, ec2_account_response, skip_none=True)),
        201
    )


@blueprint.route('/', methods=['GET'])
def get_ec2_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    account = get_ec2_account_for_user(name, user_id)
    return make_response(
        jsonify(marshal(account, ec2_account_response, skip_none=True)),
        200
    )


@blueprint.route('/group_accounts', methods=['GET'])
def get_accounts_in_group():
    data = json.loads(request.data.decode())
    group_name = data['group_name']
    user_id = data['user_id']

    try:
        accounts = get_accounts_in_ec2_group(group_name, user_id)
    except Exception as error:
        return make_response(jsonify({'msg': str(error)}), 404)

    accounts = [
        marshal(
            account,
            ec2_account_response,
            skip_none=True
        ) for account in accounts
    ]
    return make_response(jsonify(accounts), 200)


@blueprint.route('/list/<string:user>', methods=['GET'])
def get_ec2_account_list(user):
    accounts = get_ec2_accounts(user)
    accounts = [marshal(account, ec2_account_response, skip_none=True) for account in accounts]
    return make_response(jsonify(accounts), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_ec2_account():
    data = json.loads(request.data.decode())
    name = data['name']
    user_id = data['user_id']

    try:
        rows_deleted = delete_ec2_account_for_user(name, user_id)
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Delete EC2 account failed'}),
            400
        )

    return make_response(
        jsonify({'rows_deleted': rows_deleted}),
        200
    )


@blueprint.route('/', methods=['PUT'])
def update_ec2_account():
    data = json.loads(request.data.decode())

    try:
        account = update_ec2_account_for_user(
            data['account_name'],
            data['user_id'],
            data.get('additional_regions'),
            data.get('credentials'),
            data.get('group'),
            data.get('region'),
            data.get('subnet')
        )
    except Exception as error:
        current_app.logger.warning(error)
        return make_response(
            jsonify({'msg': 'Update EC2 account failed'}),
            400
        )

    return make_response(
        jsonify(marshal(account, ec2_account_response, skip_none=True)),
        200
    )
