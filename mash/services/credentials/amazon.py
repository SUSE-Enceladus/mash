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
    Implements credentials handling for Amazon.
    """
    def post_init(self):
        """
        Initialize secret information we need to access Amazon EC2
        """
        self.access_key_id = None
        self.secret_access_key = None
        self.ssh_key_name = None
        self.ssh_private_key = None

    def set_credentials(
        self, access_key_id, secret_access_key, ssh_key_name, ssh_private_key
    ):
        """
        Initialize secret information we need to access Amazon EC2.
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.ssh_key_name = ssh_key_name
        self.ssh_private_key = ssh_private_key
