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

from datetime import datetime
from flask_jwt_extended import decode_token

from sqlalchemy.orm.exc import NoResultFound

from mash.services.database.extensions import db
from mash.services.database.models import (
    User,
    Token
)
from mash.services.api.utils.users import get_user_by_id


def _epoch_utc_to_datetime(epoch_utc):
    """
    Convert epoch timestamp into datetime.
    """
    return datetime.fromtimestamp(epoch_utc)


def add_token_to_database(encoded_token, user_id):
    """
    Add a new token to the database.
    """
    decoded_token = decode_token(encoded_token)
    jti = decoded_token['jti']
    token_type = decoded_token['type']

    if 'exp' in decoded_token:
        expires = _epoch_utc_to_datetime(decoded_token['exp'])
    else:
        expires = None

    token = Token(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires=expires
    )
    db.session.add(token)
    db.session.commit()


def is_token_revoked(decoded_token):
    """
    Checks if the given token exists.
    """
    jti = decoded_token['jti']

    try:
        Token.query.filter_by(jti=jti).one()
    except NoResultFound:
        return True


def get_user_tokens(user_id):
    """
    Returns all of the tokens for given user.
    """
    user = get_user_by_id(user_id)
    return user.tokens


def get_token_by_jti(token_jti, user_id):
    """
    Get token by jti identifier.
    """
    user = get_user_by_id(user_id)
    token = Token.query.filter(
        User.id == user.id
    ).filter_by(jti=token_jti).first()

    return token


def revoke_token_by_jti(jti, user_id):
    """
    Revoke token by jti identifier.
    """
    token = get_token_by_jti(jti, user_id)

    if token:
        db.session.delete(token)
        db.session.commit()
        return 1
    else:
        return 0


def revoke_tokens(user_id):
    """
    Revokes (deletes) all tokens for given user.
    """
    user = get_user_by_id(user_id)
    rows_deleted = len(user.tokens)
    user.tokens = []
    db.session.commit()
    return rows_deleted


def prune_expired_tokens():
    """
    Delete tokens that have expired from the database.
    """
    now = datetime.now()
    rows_deleted = Token.query.filter(Token.expires < now).delete()
    db.session.commit()

    return rows_deleted
