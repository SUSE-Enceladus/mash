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

from flask import current_app
from flask_jwt_extended import decode_token

from mash.utils.mash_utils import handle_request


def add_token_to_database(encoded_token, user_id):
    """
    Add a new token to the database.
    """
    decoded_token = decode_token(encoded_token)
    jti = decoded_token['jti']
    token_type = decoded_token['type']
    expires = decoded_token['exp']

    handle_request(
        current_app.config['DATABASE_API_URL'],
        'tokens/',
        'post',
        job_data={
            'jti': jti,
            'token_type': token_type,
            'user_id': user_id,
            'expires': expires
        }
    )


def is_token_revoked(decoded_token):
    """
    Checks if the given token exists.
    """
    jti = decoded_token['jti']
    user_id = decoded_token['sub']
    token = get_token_by_jti(jti, user_id)

    if token:
        return False
    else:
        return True


def get_user_tokens(user_id):
    """
    Returns all of the tokens for given user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'tokens/list/{user}'.format(user=user_id),
        'get'
    )

    return response.json()


def get_token_by_jti(token_jti, user_id):
    """
    Get token by jti identifier.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'tokens/',
        'get',
        job_data={
            'jti': token_jti,
            'user_id': user_id
        }
    )

    return response.json()


def revoke_token_by_jti(jti, user_id):
    """
    Revoke token by jti identifier.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'tokens/',
        'delete',
        job_data={
            'jti': jti,
            'user_id': user_id
        }
    )
    return response.json()['rows_deleted']


def revoke_tokens(user_id):
    """
    Revokes (deletes) all tokens for given user.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'tokens/list/{user}'.format(user=user_id),
        'delete'
    )
    return response.json().get('rows_deleted', 0)
