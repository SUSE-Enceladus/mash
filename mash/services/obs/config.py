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

from mash.services.obs.defaults import Defaults
from mash.exceptions import MashConfigError


class OBSConfig(object):
    """
    Implements reading of obs service configuration file:

    * /etc/mash/obs_config.yml

    The mash configuration file for the obs service is a yaml
    formatted file containing information to control the behavior
    of the obs service.
    """
    def __init__(self, config_file=Defaults.get_config()):
        self.config_data = None
        try:
            with open(config_file, 'r') as config:
                self.config_data = yaml.load(config)
        except Exception as e:
            raise MashConfigError(
                'Failed reading config file: {config}: {error}'.format(
                    config=config_file, error=e
                )
            )

    def get_log_port(self):
        """
        Return logger port:

        obs:
          log_port: 9001

        if no configuration exists the log port from
        the Defaults class is returned

        :rtype: int
        """
        log_port = self._get_attribute(
            element='obs', attribute='log_port'
        )
        return log_port if log_port else \
            Defaults.get_log_port()

    def get_control_port(self):
        """
        Return control port:

        obs:
          control_port: 9000

        if no configuration exists the control port from
        the Defaults class is returned

        :rtype: int
        """
        control_port = self._get_attribute(
            element='obs', attribute='control_port'
        )
        return control_port if control_port else \
            Defaults.get_control_port()

    def get_log_file(self):
        """
        Return log file name:

        obs:
          logfile: /tmp/obs_service.log

        if no configuration exists the log file name from
        the Defaults class is returned

        :rtype: string
        """
        logfile = self._get_attribute(
            element='obs', attribute='logfile'
        )
        return logfile if logfile else \
            Defaults.get_log_file()

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
            element='obs', attribute='download_directory'
        )
        return download_directory if download_directory else \
            Defaults.get_download_dir()

    def _get_attribute(self, element, attribute):
        if self.config_data:
            if element in self.config_data:
                if attribute in self.config_data[element]:
                    return self.config_data[element][attribute]
