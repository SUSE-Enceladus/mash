# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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

from unittest.mock import Mock, patch
from mash.utils.gce import cleanup_gce_image
from mash.utils.gce import get_region_list


@patch('mash.utils.gce.get_driver')
def test_get_client(mock_get_driver):
    compute_engine = Mock()
    driver = Mock()
    mock_get_driver.return_value = compute_engine
    compute_engine.return_value = driver

    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }

    cleanup_gce_image(creds, 'image_123')

    driver.ex_delete_image.assert_called_once_with('image_123')


@patch('mash.utils.gce.get_driver')
def test_get_region_list(mock_get_driver):
    compute_engine = Mock()
    driver = Mock()
    mock_get_driver.return_value = compute_engine
    compute_engine.return_value = driver
    driver.ex_list_regions.return_value = []

    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }

    get_region_list(creds)

    driver.ex_list_regions.assert_called_once()
