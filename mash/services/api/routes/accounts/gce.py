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
from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.schema.accounts.gce import (
    add_account_gce,
    gce_account_update
)
from mash.services.api.utils.accounts.gce import (
    create_gce_account,
    get_gce_account,
    get_gce_accounts,
    delete_gce_account,
    update_gce_account
)

api = Namespace(
    'GCE Accounts',
    description='GCE account operations'
)
add_gce_account_request = api.schema_model('gce_account', add_account_gce)
update_gce_account_request = api.schema_model(
    'gce_account_update',
    gce_account_update
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)

gce_account_response = Model(
    'gce_account_response', {
        'id': fields.String,
        'name': fields.String,
        'bucket': fields.String,
        'region': fields.String,
        'testing_account': fields.String,
        'is_publishing_account': fields.String
    }
)

api.models['gce_account_response'] = gce_account_response


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class GCEAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for GCE.
    """

    @api.doc('create_gce_account')
    @jwt_required
    @api.expect(add_gce_account_request)
    @api.response(201, 'GCE account created', gce_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(409, 'Duplicate account', default_response)
    def post(self):
        """
        Create a new GCE account.
        """
        data = json.loads(request.data.decode())

        try:
            account = create_gce_account(
                get_jwt_identity(),
                data['account_name'],
                data['bucket'],
                data['region'],
                data['credentials'],
                data.get('testing_account'),
                data.get('is_publishing_account', False)
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
                jsonify({'msg': 'Failed to add GCE account'}),
                400
            )

        return make_response(
            jsonify(marshal(account, gce_account_response, skip_none=True)),
            201
        )

    @api.doc('get_gce_accounts')
    @jwt_required
    @api.marshal_list_with(gce_account_response, skip_none=True)
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all GCE accounts.
        """
        gce_accounts = get_gce_accounts(get_jwt_identity())
        return gce_accounts


@api.route('/<string:name>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class GCEAccount(Resource):
    @api.doc('delete_gce_account')
    @jwt_required
    @api.response(200, 'GCE account deleted', default_response)
    @api.response(400, 'Delete GCE account failed', default_response)
    @api.response(404, 'Not found', default_response)
    def delete(self, name):
        """
        Delete GCE account matching name for requesting user.
        """
        try:
            rows_deleted = delete_gce_account(name, get_jwt_identity())
        except Exception:
            return make_response(
                jsonify({'msg': 'Delete GCE account failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'GCE account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'GCE account not found'}),
                404
            )

    @api.doc('get_gce_account')
    @jwt_required
    @api.response(200, 'Success', gce_account_response)
    @api.response(404, 'Not found', default_response)
    def get(self, name):
        """
        Get GCE account.
        """
        account = get_gce_account(name, get_jwt_identity())

        if account:
            return make_response(
                jsonify(marshal(account, gce_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'GCE account not found'}),
                404
            )

    @api.doc('update_gce_account')
    @jwt_required
    @api.expect(update_gce_account_request)
    @api.response(200, 'Success', gce_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(404, 'Not found', default_response)
    def post(self, name):
        """
        Update GCE account.
        """
        data = json.loads(request.data.decode())

        try:
            account = update_gce_account(
                name,
                get_jwt_identity(),
                data.get('bucket'),
                data.get('region'),
                data.get('credentials'),
                data.get('testing_account')
            )
        except Exception as error:
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        if account:
            return make_response(
                jsonify(marshal(account, gce_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'GCE account not found'}),
                404
            )
