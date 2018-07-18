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


class UploaderConfig(BaseConfig):
    """
    Implements reading of uploader service configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file for the uploader service is a yaml
    formatted file containing information to control the behavior
    of the uploader service.

    uploader:
      azure:
        # chunk size in bytes, default value taken from azure SDK
        max_chunk_byte_size: 4096
        # max retries on block upload error
        max_chunk_retry_attempts: 5
    """
    def __init__(self, config_file=None):
        super(UploaderConfig, self).__init__(config_file)
        self.azure_uploader = self._get_attribute('azure', 'uploader') or dict()

    def get_azure_max_chunk_byte_size(self):
        return self.azure_uploader.get('max_chunk_byte_size') or \
            Defaults.get_azure_max_chunk_byte_size()

    def get_azure_max_chunk_retry_attempts(self):
        return self.azure_uploader.get('max_chunk_retry_attempts') or \
            Defaults.get_azure_max_chunk_retry_attempts()
