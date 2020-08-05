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

from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound

from mash.services.database.models import Token
from mash.services.database.extensions import db
from mash.services.database.utils.users import get_user_by_id


def _epoch_utc_to_datetime(epoch_utc):
    """
    Convert epoch timestamp into datetime.
    """
    return datetime.fromtimestamp(epoch_utc)


def add_user_token(jti, token_type, user_id, expires):
    """
    Add a new token to the database.
    """
    if expires:
        expires = _epoch_utc_to_datetime(expires)

    token = Token(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires=expires
    )
    db.session.add(token)
    db.session.commit()


def get_token_by_jti(jti, user_id):
    """
    Get token by jti identifier.
    """
    try:
        token = Token.query.filter_by(
            user_id=user_id,
            jti=jti
        ).one()
    except NoResultFound:
        token = None

    return token


def get_user_tokens(user_id):
    """
    Returns all of the tokens for given user.
    """
    user = get_user_by_id(user_id)
    return user.tokens


def revoke_token_by_jti(jti, user_id):
    """
    Revoke token by jti identifier.
    """
    token = get_token_by_jti(jti, user_id)

    if token:
        db.session.delete(token)
        db.session.commit()
        return 1

    return 0


def revoke_user_tokens(user_id):
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
