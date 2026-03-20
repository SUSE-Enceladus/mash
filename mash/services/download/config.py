# Copyright (c) 2026 SUSE LLC.  All rights reserved.
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


class DownloadConfig(BaseConfig):
    """
    Implements reading of test configuration from the mash
    configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """

    def __init__(self, config_file=None):
        super(DownloadConfig, self).__init__(config_file)

    def get_download_data(self):
        """
        Provides the configuration data for the download service
        """
        data = self._get_attribute(attribute='download')

        if not data:
            return {}

        return data

    def get_download_additional_file_extensions(self):
        """
        Provides the configured additional extensions that are configured for
        the download service.

        When that parameter is configured, the service will attempt to
        download the files with similar base name as the image downloaded but
        having those extensions
        """
        download_info = self.get_download_data()
        additional_file_extensions = download_info.get(
            'additional_file_extensions',
            []
        )
        return additional_file_extensions

    def get_download_additional_prefixed_files(self):
        """
        Provides the configured additional prefixed files that are configured
        for the download service.

        When that parameter is configured, the service will attempt to
        download the files appending the prefix to the base image name and
        postpending the extensions for the prefix
        """
        download_info = self.get_download_data()
        additional_prefixed_files = download_info.get(
            'additional_prefixed_files',
            {}
        )
        return additional_prefixed_files
