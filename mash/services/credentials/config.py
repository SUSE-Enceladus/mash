# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

from mash.services.base_config import BaseConfig
from mash.services.credentials.defaults import Defaults


class CredentialsConfig(BaseConfig):
    """
    Implements reading of credentials configuration from the mash
    configuration file.

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """

    def __init__(self, config_file=None):
        super(CredentialsConfig, self).__init__(config_file)

    def get_accounts_file(self):
        """
        Return the path to the provider accounts key file.

        :rtype: string
        """
        accounts_file = self._get_attribute(
            attribute='accounts_file',
            element='jobcreator'
        )
        return accounts_file or Defaults.get_accounts_file()

    def get_credentials_dir(self):
        """
        Return directory path for credentials directory.

        credentials:
          credentials_directory: /var/lib/mash/credentials

        If no configuration exists the credentials dir path from
        the Defaults class is returned.

        :rtype: string
        """
        credentials_directory = self._get_attribute(
            attribute='credentials_directory', element='credentials'
        )
        return credentials_directory if credentials_directory else \
            Defaults.get_credentials_dir()
