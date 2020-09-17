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

import string

from secrets import choice
from flask import current_app
from sqlalchemy.exc import IntegrityError

from mash.services.database.models import User
from mash.services.database.extensions import db
from mash.mash_exceptions import MashDBException
from mash.utils.mash_utils import handle_request


def add_new_user(email, password=None):
    """
    Add new user to database and set password hash.

    If the user or email exists return None.
    """
    if not password:
        password = ''.join(
            [choice(string.ascii_letters + string.digits) for _ in range(64)]
        )

    user = User(email=email)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as error:
        current_app.logger.warning(error)
        db.session.rollback()
        return None

    return user


def get_user_by_id(user_id):
    """
    Retrieve user from database if a match exists.

    If user does not exist return None.
    """
    user = User.query.filter_by(id=user_id).first()
    return user


def get_user_by_email(email, create=False):
    """
    Retrieve user from database if a match exists.

    If the user does not exist and create is True, the user
    is created on the fly. Otherwise None is returned.
    """
    user = User.query.filter_by(email=email).first()
    if not user and create is True:
        user = add_new_user(email)
    return user


def delete_user_by_id(user_id):
    """
    Delete user by id.

    If user does not exist return 0.
    """
    user = get_user_by_id(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
        handle_request(
            current_app.config['CREDENTIALS_URL'],
            'credentials/{user}'.format(user=user_id),
            'delete'
        )
        return 1
    else:
        return 0


def verify_login(email, password):
    """
    Compare password hashes.

    If hashes match the user is authenticated
    and user instance is returned.
    """
    user = get_user_by_email(email)

    if user and user.password_dirty:
        raise MashDBException(
            'Password change is required before you can login.'
        )
    elif user and user.check_password(password):
        return user
    else:
        return None


def reset_user_password(email):
    """
    Reset password for user if user exists.

    Create a random password and send an email to perform change
    password. Also, remove any active sessions the user currently
    has open and set password to dirty to prevent login with
    temporary password.

    If user does not exist return 0.
    """
    user = get_user_by_email(email)

    if user:
        password = ''.join(
            [choice(string.ascii_letters + string.digits) for _ in range(24)]
        )
        user.set_password(password)
        user.password_dirty = True
        user.tokens = []  # Revoke all user sessions
        db.session.commit()
        return password
    else:
        return None


def change_user_password(email, current_password, new_password):
    """
    Change password for user if user exists and existing password matches.

    And reset the password to clean so the user can login again.

    If user does not exist return 0.
    """
    user = get_user_by_email(email)

    if user and user.check_password(current_password):
        user.set_password(new_password)
        user.password_dirty = False
        db.session.commit()
        return 1
    else:
        return 0
