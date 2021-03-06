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

from mash.services.base_config import BaseConfig
from mash.services.cleanup.defaults import Defaults as CleanupDefaults


class CleanupConfig(BaseConfig):
    """
    Implements reading of cleanup configuration from mash configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """
    def __init__(self, config_file=None):
        super(CleanupConfig, self).__init__(config_file)

    def get_max_image_age(self):
        """
        Return maximum image age (in days):

        cleanup:
          max_image_age: 90

        if no configuration exists the max image age from
        the Defaults class is returned

        :rtype: int
        """
        max_image_age = self._get_attribute(
            attribute='max_image_age', element='cleanup'
        )
        return max_image_age if max_image_age else \
            CleanupDefaults.get_max_image_age()
