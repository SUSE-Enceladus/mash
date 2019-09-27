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

from flask import Blueprint, current_app, jsonify, request, make_response

blueprint = Blueprint('credentials', __name__, url_prefix='/credentials')


@blueprint.route('/', methods=['POST'])
def add_credentials():
    data = json.loads(request.data.decode())

    try:
        current_app.credentials_datastore.save_credentials(
            data['cloud'],
            data['account_name'],
            data['requesting_user'],
            data['credentials']
        )
    except Exception as error:
        msg = 'Unable to save credentials: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(jsonify({'msg': 'Credentials saved'}), 201)


@blueprint.route('/', methods=['GET'])
def get_credentials():
    data = json.loads(request.data.decode())

    try:
        credentials = current_app.credentials_datastore.retrieve_credentials(
            data['cloud_accounts'],
            data['cloud'],
            data['requesting_user']
        )
    except Exception as error:
        msg = 'Unable to retrieve credentials: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(jsonify(credentials), 200)


@blueprint.route('/', methods=['DELETE'])
def delete_credentials():
    data = json.loads(request.data.decode())

    try:
        current_app.credentials_datastore.delete_credentials(
            data['requesting_user'],
            data['account_name'],
            data['cloud']
        )
    except Exception as error:
        msg = 'Unable to delete credentials: {0}'.format(error)
        current_app.logger.warning(msg)
        return make_response(jsonify({'msg': msg}), 400)

    return make_response(jsonify({'msg': 'Credentials deleted'}), 200)
