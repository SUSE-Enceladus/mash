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
from flask_restplus import fields, marshal, Model, Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)

from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashException
from mash.services.api.utils.accounts.ec2 import (
    create_ec2_account,
    get_ec2_accounts,
    get_ec2_account,
    delete_ec2_account
)
from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.schema.accounts.ec2 import add_account_ec2

api = Namespace(
    'EC2 Accounts',
    description='EC2 account operations'
)
add_ec2_account_request = api.schema_model(
    'add_ec2_account_request',
    add_account_ec2
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)

region = Model(
    'region', {
        'id': fields.String,
        'name': fields.String,
        'helper_image': fields.String
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
        'additional_regions': api.as_list(
            fields.Nested(region, skip_none=True)
        ),
        'group': fields.Nested(group, skip_none=True)
    }
)

api.models['region'] = region
api.models['group'] = group
api.models['ec2_account_response'] = ec2_account_response
api.models['default_response'] = default_response


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class EC2AccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for EC2.
    """

    @api.doc('create_ec2_account')
    @jwt_required
    @api.expect(add_ec2_account_request)
    @api.response(201, 'Created EC2 account', ec2_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(409, 'Duplicate account', default_response)
    def post(self):
        """
        Create a new EC2 account.
        """
        data = json.loads(request.data.decode())

        try:
            account = create_ec2_account(
                get_jwt_identity(),
                data['account_name'],
                data['partition'],
                data['region'],
                data['credentials'],
                data.get('subnet'),
                data.get('group'),
                data.get('additional_regions')
            )
        except MashException as error:
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )
        except IntegrityError:
            return make_response(
                jsonify({'msg': 'Account already exists'}),
                409
            )
        except Exception:
            return make_response(
                jsonify({'msg': 'Failed to add EC2 account'}),
                400
            )

        return make_response(
            jsonify(marshal(account, ec2_account_response, skip_none=True)),
            201
        )

    @api.doc('get_ec2_accounts')
    @jwt_required
    @api.marshal_list_with(ec2_account_response, skip_none=True)
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all EC2 accounts.
        """
        ec2_accounts = get_ec2_accounts(get_jwt_identity())
        return ec2_accounts


@api.route('/<string:name>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class EC2Account(Resource):
    @api.doc('delete_ec2_account')
    @jwt_required
    @api.response(200, 'EC2 account deleted', default_response)
    @api.response(400, 'Delete EC2 account failed', default_response)
    @api.response(404, 'Not found', default_response)
    def delete(self, name):
        """
        Delete EC2 account.
        """
        try:
            rows_deleted = delete_ec2_account(name, get_jwt_identity())
        except Exception:
            return make_response(
                jsonify({'msg': 'Delete EC2 account failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'EC2 account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'EC2 account not found'}),
                404
            )

    @api.doc('get_ec2_account')
    @jwt_required
    @api.response(200, 'Success', ec2_account_response)
    @api.response(404, 'Not found', default_response)
    def get(self, name):
        """
        Get EC2 account.
        """
        account = get_ec2_account(name, get_jwt_identity())

        if account:
            return make_response(
                jsonify(marshal(account, ec2_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'EC2 account not found'}),
                404
            )
