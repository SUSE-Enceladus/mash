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
from mash.services.testing.defaults import Defaults


class TestingConfig(BaseConfig):
    """
    Implements reading of testing service configuration file:

    * /etc/mash/testing_config.yml

    The mash configuration file for the testing service is a yaml
    formatted file containing information to control the behavior
    of the testing service.
    """
    __test__ = False

    def __init__(self, config_file=Defaults.get_config()):
        super(TestingConfig, self).__init__(config_file)
