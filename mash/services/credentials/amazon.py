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
# project
from mash.services.credentials.base import CredentialsBase


class CredentialsAmazon(CredentialsBase):
    """
    Implements credentials handling for Amazon
    """
    def post_init(self):
        """
        Initialize secret information we need to access Amazon EC2
        """
        self.credentials = {
            'ssh_key_pair_name': None,
            'ssh_key_private_key_file': None,
            'access_key': None,
            'secret_key': None
        }

    def set_credentials(self, secret_token):
        self.secret_token = secret_token

    def get_credentials(self):
        # TODO: fill in secret information from token
        return self.credentials
