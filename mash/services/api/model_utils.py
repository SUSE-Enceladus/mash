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

from sqlalchemy.exc import IntegrityError

from mash.services.api.extensions import db
from mash.services.api.models import (
    User
)


def add_user(username, email, password):
    """
    Add new user to database and set password hash.

    If the user or email exists return None.
    """
    user = User(
        username=username,
        email=email
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None

    return user


def verify_login(username, password):
    """
    Compare password hashes.

    If hashes match the user is authenticated
    and user instance is returned.
    """
    user = get_user_by_username(username)

    if user and user.check_password(password):
        return user
    else:
        return None


def get_user_by_username(username):
    """
    Retrieve user from database if a match exists.

    Otherwise None is returned.
    """
    user = User.query.filter_by(username=username).first()
    return user


def get_user_email(username):
    """
    Retrieve user email if user exists.
    """
    user = get_user_by_username(username)

    if user:
        return user.email


def delete_user(username):
    """
    Delete user by username.

    If user does not exist return 0.
    """
    user = get_user_by_username(username)

    if user:
        db.session.delete(user)
        db.session.commit()
        return 1
    else:
        return 0
