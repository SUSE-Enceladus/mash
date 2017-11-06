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

import os

from mash.mash_exceptions import MashLoggerException
from mash.services.base_config import BaseConfig
from mash.services.logger.defaults import Defaults


class LoggerConfig(BaseConfig):
    """
    Implements reading of logger service configuration file:

    * /etc/mash/logger_config.yml

    The mash configuration file for the logger service is a yaml
    formatted file containing information to control the behavior
    of the logger service.
    """
    def __init__(self, config_file=Defaults.get_config()):
        super(LoggerConfig, self).__init__(config_file)

    def get_log_dir(self):
        """
        Return log directory:

        logger:
          log_dir: /var/log/mash/

        if no configuration exists the log directory from
        constants is returned

        :rtype: string
        """
        log_dir = self._get_attribute(
            element='logger', attribute='log_dir'
        )
        log_dir = log_dir or Defaults.get_log_dir()

        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception as e:
                raise MashLoggerException(
                    'Could not make logging directory: {}'.format(e)
                )

        return log_dir

    def get_log_file(self, file_name):
        """
        Return log file given the file_name:

        :rtype: string
        """
        log_file = os.path.join(
            self.get_log_dir(), ''.join([file_name, '.log'])
        )
        return os.path.expanduser(os.path.normpath(log_file))
