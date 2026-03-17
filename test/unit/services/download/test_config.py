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

import unittest

from mash.services.download.config import DownloadConfig


class TestDownloadConfig(unittest.TestCase):

    def setUp(self):
        self.config = DownloadConfig(config_file='test/data/mash_config.yaml')

    def test_get_download_data(self):

        self.assertEqual(
            self.config.get_download_data(),
            {
                'additional_file_extensions': [
                    'cdx.json',
                    'spdx.json',
                    'packages'
                ],
                'additional_prefixed_files': {
                    'ChangeLog.': [
                        'txt',
                        'json'
                    ]
                }
            }
        )

    def test_get_additional_file_extensions(self):
        self.assertEqual(
            self.config.get_download_additional_file_extensions(),
            [
                'cdx.json',
                'spdx.json',
                'packages'
            ]
        )

    def test_get_additional_prefixed_files(self):

        self.assertEqual(
            self.config.get_download_additional_prefixed_files(),
            {
                'ChangeLog.': [
                    'txt',
                    'json'
                ]
            }
        )
