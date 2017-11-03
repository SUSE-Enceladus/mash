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
from mash.services.uploader.credentials.base import CredentialsBase


class CredentialsAmazon(CredentialsBase):
    """
    Implements credentials handling for Amazon
    """
    def post_init(self):
        self.credentials = {
            'ssh_key_pair_name': self._get_ssh_key_pair_name(),
            'ssh_key_private_key_file': self._get_ssh_key_private_key_file(),
            'access_key': self._get_access_key(),
            'secret_key': self._get_secret_key()
        }

    def get_credentials(self):
        return self.credentials

    def _get_ssh_key_pair_name(self):
        # TODO: from a database
        pass

    def _get_ssh_key_private_key_file(self):
        # TODO: from a database
        pass

    def _get_access_key(self):
        # TODO: from a database
        pass

    def _get_secret_key(self):
        # TODO: from a database
        pass
