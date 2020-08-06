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

from mash.services.api.variables import (
    password_change_msg_template,
    password_reset_msg_template
)
from mash.mash_exceptions import MashDBException
from mash.utils.mash_utils import handle_request


def add_user(email, password=None):
    """
    Add new user to database and set password hash.

    If the user or email exists return None.
    If password is None, a random password is created, in effect creating
    an account that can only be used with oidc authentication.
    """
    if password and len(password) < 8:
        raise MashDBException(
            'Password too short. Minimum length is 8 characters.'
        )

    if not email_in_whitelist(email):
        raise MashDBException(
            'Cannot create a user with the provided email. Access denied.'
        )

    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/',
        'post',
        job_data={
            'email': email,
            'password': password
        }
    )

    return response.json()


def email_in_whitelist(email):
    """
    Check if given email address is in whitelist.
    """
    email_whitelist = current_app.config['EMAIL_WHITELIST']
    if email_whitelist and email not in email_whitelist:
        return False

    domain_whitelist = current_app.config['DOMAIN_WHITELIST']
    if domain_whitelist and email.split('@')[1].strip() not in domain_whitelist:
        return False

    return True


def verify_login(email, password):
    """
    Compare password hashes.

    If hashes match the user is authenticated
    and user instance is returned.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/login/',
        'post',
        job_data={
            'email': email,
            'password': password
        }
    )
    return response.json()


def get_user_by_email(email, create=False):
    """
    Retrieve user from database if a match exists.

    If the user does not exist and create is True, the user
    is created on the fly. Otherwise None is returned.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/get_user/{email}'.format(email=email),
        'get',
        job_data={
            'create': create
        }
    )
    return response.json()


def get_user_by_id(user_id):
    """
    Retrieve user from database if a match exists.

    If user does not exist return None.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/{user}'.format(user=user_id),
        'get'
    )
    return response.json()


def delete_user(user_id):
    """
    Delete user by id.

    If user does not exist return 0.
    """
    try:
        handle_request(
            current_app.config['DATABASE_API_URL'],
            'users/{user}'.format(user=user_id),
            'delete'
        )
    except Exception:
        return 0

    return 1


def reset_user_password(email):
    """
    Reset password for user if user exists.

    Create a random password and send an email to perform change
    password. Also, remove any active sessions the user currently
    has open and set password to dirty to prevent login with
    temporary password.

    If user does not exist return 0.
    """
    response = handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/password/reset/{email}'.format(email=email),
        'post'
    )
    password = response.json()['password']

    current_app.notification_class.send_notification(
        password_reset_msg_template.format(password=password),
        '[MASH] Password Reset',
        email
    )


def change_user_password(email, current_password, new_password):
    """
    Change password for user if user exists and existing password matches.

    And reset the password to clean so the user can login again.
    """
    if len(new_password) < 8:
        raise MashDBException(
            'Password too short. Minimum length is 8 characters.'
        )

    handle_request(
        current_app.config['DATABASE_API_URL'],
        'users/password/change/{email}'.format(email=email),
        'post',
        job_data={
            'current_password': current_password,
            'new_password': new_password
        }
    )

    current_app.notification_class.send_notification(
        password_change_msg_template,
        '[MASH] Password Changed',
        email
    )
