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
import yaml

from mash.mash_exceptions import MashConfigException
from mash.services.base_defaults import Defaults


class BaseConfig(object):
    """
    Implements reading of a yaml configuration file:

    The mash configuration files are yaml formatted files containing
    information to control the behavior of each service.
    """
    def __init__(self, config_file=None):
        config_file = config_file or Defaults.get_config()
        self.config_data = None
        try:
            with open(config_file, 'r') as config:
                self.config_data = yaml.load(config)
        except Exception as e:
            raise MashConfigException(
                'Failed reading config file: {config}: {error}'.format(
                    config=config_file, error=e
                )
            )

    def _get_attribute(self, attribute, element=None):
        if self.config_data:
            if element:
                if self.config_data.get(element):
                    return self.config_data[element].get(attribute)
            else:
                return self.config_data.get(attribute)

    def get_jwt_secret(self):
        """
        Return JWT secret token from MASH config file.

        Raise exception if secret not in config file.
        """
        secret = self._get_attribute(attribute='jwt_secret')

        if not secret:
            raise MashConfigException('jwt_secret must be in config file.')

        return secret

    def get_log_directory(self):
        log_dir = self._get_attribute(attribute='log_dir')
        return log_dir or Defaults.get_log_directory()

    def get_log_file(self, service):
        """
        Return log file name based on log_dir attribute.

        :rtype: string
        """
        log_dir = self.get_log_directory()
        return '{dir}{service}_service.log'.format(
            dir=log_dir, service=service
        )
