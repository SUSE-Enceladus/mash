# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
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
import jwt


class CredentialsBase(object):
    """
    Base class credentials interface class
    """
    def __init__(self, custom_args=None):
        self.custom_args = custom_args
        self.post_init()

    def post_init(self):
        self.credentials = {}

    def set_credentials(self, secret_token):
        self.credentials.update(
            jwt.decode(secret_token, 'secret', algorithms=['HS256'])
        )

    def get_credentials(self):
        return self.credentials
