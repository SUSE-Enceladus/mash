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

from mash.services.base_config import BaseConfig
from mash.services.obs.defaults import Defaults


class OBSConfig(BaseConfig):
    """
    Implements reading of obs configuration from mash configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """
    def __init__(self, config_file=None):
        super(OBSConfig, self).__init__(config_file)

    def get_download_directory(self):
        """
        Return directory name for image download directory:

        obs:
          download_directory: /tmp

        if no configuration exists the download dir name from
        the Defaults class is returned

        :rtype: string
        """
        download_directory = self._get_attribute(
            attribute='download_directory', element='obs'
        )
        return download_directory if download_directory else \
            Defaults.get_download_dir()
