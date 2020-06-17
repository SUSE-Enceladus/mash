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
from mash.services.base_defaults import Defaults


class UploadConfig(BaseConfig):
    """
    Implements reading of upload configuration from mash configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.

    upload:
      azure:
        # max retries on block upload error
        max_chunk_retry_attempts: 5
        # max number of worker threads for upload
        max_workers: 16
    """
    def __init__(self, config_file=None):
        super(UploadConfig, self).__init__(config_file)
        self.azure_upload = self._get_attribute('azure', 'upload') or dict()

    def get_azure_max_retry_attempts(self):
        return self.azure_upload.get('max_retry_attempts') or \
            Defaults.get_azure_max_retry_attempts()

    def get_azure_max_workers(self):
        return self.azure_upload.get('max_workers') or \
            Defaults.get_azure_max_workers()
