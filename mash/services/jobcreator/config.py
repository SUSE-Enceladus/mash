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
from mash.services.jobcreator.defaults import Defaults


class JobCreatorConfig(BaseConfig):
    """
    Implements reading of job creator service configuration file:

    * /etc/mash/job_creator_config.yml

    The mash configuration file for the job creator service is a yaml
    formatted file containing information to control the behavior
    of the job creator service.
    """

    def __init__(self, config_file=Defaults.get_config()):
        super(JobCreatorConfig, self).__init__(config_file)

    def get_log_file(self):
        """
        Return log file name:
        jobcreator:
          logfile: /var/log/mash/job_creator_service.log

        If no configuration exists the log file name from the
        Defaults class is returned
        :rtype: string
        """
        logfile = self._get_attribute(
            element='jobcreator', attribute='logfile'
        )
        return logfile if logfile else Defaults.get_log_file()
