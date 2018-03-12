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

from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig


class TestingConfig(BaseConfig):
    """
    Implements reading of the mash configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """
    __test__ = False

    def __init__(self, config_file=None):
        super(TestingConfig, self).__init__(config_file)

    def get_ssh_private_key_file(self):
        """
        Return the path to the ssh private key file.

        :rtype: string
        """
        private_key_file = self._get_attribute(
            attribute='ssh_private_key_file', element='testing'
        )

        if not private_key_file:
            raise MashConfigException(
                'ssh_private_key_file is required in configuration file for '
                'testing service.'
            )

        return private_key_file
