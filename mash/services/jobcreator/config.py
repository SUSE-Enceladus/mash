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
from mash.services.jobcreator.defaults import Defaults


class JobCreatorConfig(BaseConfig):
    """
    Implements reading of mash configuration file:

    * /etc/mash/mash_config.yml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of mash.
    """

    def __init__(self, config_file=None):
        super(JobCreatorConfig, self).__init__(config_file)

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
