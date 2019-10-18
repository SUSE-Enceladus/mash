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
from mash.utils.gce import (
    cleanup_gce_image,
    get_region_list,
    delete_gce_image,
    delete_image_tarball
)


@patch('mash.utils.gce.delete_image_tarball')
@patch('mash.utils.gce.delete_gce_image')
def test_cleanup_gce_image(mock_delete_image, mock_delete_tarball):
    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }
    cleanup_gce_image(creds, 'image_123', 'bucket')

    assert mock_delete_image.call_count == 1
    assert mock_delete_tarball.call_count == 1


@patch('mash.utils.gce.get_driver')
def test_delete_gce_image(mock_get_driver):
    compute_engine = Mock()
    driver = Mock()
    mock_get_driver.return_value = compute_engine
    compute_engine.return_value = driver

    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }

    delete_gce_image(creds, 'auth_file', 'image_123')

    driver.ex_delete_image.assert_called_once_with('image_123')


@patch('mash.utils.gce.GoogleStorageDriver')
def test_delete_image_tarball(mock_get_driver):
    driver = Mock()
    obj = Mock()

    driver.get_object.return_value = obj
    mock_get_driver.return_value = driver

    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }

    delete_image_tarball(creds, 'auth_file', 'image_123', 'bucket')

    driver.get_object.assert_called_once_with('bucket', 'image_123.tar.gz')
    driver.delete_object.assert_called_once_with(obj)


@patch('mash.utils.gce.get_driver')
def test_get_region_list(mock_get_driver):
    compute_engine = Mock()
    driver = Mock()
    mock_get_driver.return_value = compute_engine
    compute_engine.return_value = driver

    class MockGCERegion:
        def __init__(self, name, status, zones):
            self.name = name
            self.status = status
            self.zones = zones

    class MockGCEZone:
        def __init__(self, name):
            self.name = name

    driver.ex_list_regions.return_value = \
        [MockGCERegion('us-west1', 'UP', [MockGCEZone('us-west1-c')])]

    creds = {
        'client_email': 'fake@fake.com',
        'project_id': '123'
    }

    get_region_list(creds)

    driver.ex_list_regions.assert_called_once_with()
