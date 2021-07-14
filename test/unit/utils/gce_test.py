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

from datetime import datetime

from pytest import raises

from googleapiclient.errors import HttpError

from unittest.mock import Mock, patch
from mash.utils.gce import (
    get_region_list,
    get_zones,
    create_gce_rollout,
    create_gce_image,
    delete_gce_image,
    deprecate_gce_image,
    get_gce_image,
    delete_image_tarball,
    upload_image_tarball,
    wait_on_image_ready,
    get_gce_compute_driver,
    get_gce_storage_driver,
    wait_on_operation,
    blob_exists
)
from mash.mash_exceptions import MashException


@patch('mash.utils.gce.wait_on_operation')
def test_delete_gce_image(mock_wait_on_op):
    driver = Mock()
    delete_op = Mock()
    response = Mock()
    operation = {
        'error': {
            'errors': [{'message': 'No image found!'}]
        }
    }

    driver.images.return_value = delete_op
    delete_op.delete.return_value = response
    response.execute.return_value = {'name': 'operation123'}
    mock_wait_on_op.return_value = operation

    with raises(MashException):
        delete_gce_image(driver, 'project', 'image_123')


def test_blob_exists():
    driver = Mock()
    bucket = Mock()
    blob = Mock()

    blob.exists.return_value = True
    bucket.blob.return_value = blob
    driver.get_bucket.return_value = bucket

    result = blob_exists(driver, 'image_123', 'bucket')

    assert result
    driver.get_bucket.assert_called_once_with('bucket')


def test_delete_image_tarball():
    driver = Mock()
    bucket = Mock()
    blob = Mock()

    bucket.blob.return_value = blob
    driver.get_bucket.return_value = bucket

    delete_image_tarball(driver, 'image_123', 'bucket')

    driver.get_bucket.assert_called_once_with('bucket')
    blob.delete.assert_called_once_with()


def test_upload_image_tarball():
    driver = Mock()
    bucket = Mock()
    blob = Mock()

    bucket.blob.return_value = blob
    driver.get_bucket.return_value = bucket

    upload_image_tarball(
        driver,
        'image_123.tar.gz',
        '/path/to/file.tar.gz',
        'bucket'
    )

    driver.get_bucket.assert_called_once_with('bucket')
    blob.upload_from_filename.assert_called_once_with('/path/to/file.tar.gz')


def test_get_region_list():
    driver = Mock()
    regions_op = Mock()
    response = Mock()

    driver.regions.return_value = regions_op
    regions_op.list.return_value = response
    response.execute.return_value = {
        'items': [
            {'status': 'UP', 'name': 'us-west1', 'zones': ['us-west1-c']}
        ]
    }

    zones = get_region_list(driver, 'project')

    assert 'us-west1-c' in zones


def test_get_zones_list():
    driver = Mock()
    zones_op = Mock()
    response = Mock()

    driver.zones.return_value = zones_op
    zones_op.list.return_value = response
    response.execute.return_value = {
        'items': [
            {'name': 'r3-d', 'region': 'regions/r3'},
            {'name': 'r1-b', 'region': 'regions/r1'},
            {'name': 'r3-a', 'region': 'regions/r2'},
            {'name': 'r2-a', 'region': 'regions/r2'},
            {'name': 'r1-c', 'region': 'regions/r1'},
            {'name': 'r1-a', 'region': 'regions/r1'}
        ]
    }

    zones = get_zones(driver, 'project')
    assert all(zone.startswith('zones/') for zone in zones)
    assert 'r1-c' in zones[-1]


def test_create_gce_rollout():
    driver = Mock()
    zones_op = Mock()
    response = Mock()

    driver.zones.return_value = zones_op
    zones_op.list.return_value = response
    response.execute.return_value = {
        'items': [
            {'name': 'r1-b', 'region': 'regions/r1'},
            {'name': 'r1-a', 'region': 'regions/r1'}
        ]
    }

    rollout = create_gce_rollout(driver, 'project')
    keys = rollout.keys()
    assert 'defaultRolloutTime' in keys
    assert 'locationRolloutPolicies' in keys
    policies = rollout.get('locationRolloutPolicies')
    assert len(policies) == 2
    format_str = '%Y-%m-%dT%H:%M:%SZ'
    time1 = datetime.strptime(policies.get('zones/r1-a'), format_str)
    time2 = datetime.strptime(policies.get('zones/r1-b'), format_str)
    time3 = datetime.strptime(rollout.get('defaultRolloutTime'), format_str)
    assert time1 < time2
    assert time2 < time3


@patch('mash.utils.gce.wait_on_image_ready')
@patch('mash.utils.gce.wait_on_operation')
def test_create_gce_image(mock_wait_on_op, wait_on_ready):
    driver = Mock()
    insert_op = Mock()
    response = Mock()
    operation = {
        'error': {
            'errors': [{'message': 'No image found!'}]
        }
    }

    driver.images.return_value = insert_op
    insert_op.insert.return_value = response
    response.execute.return_value = {'name': 'operation123'}
    mock_wait_on_op.return_value = operation

    with raises(MashException):
        create_gce_image(
            driver,
            'project',
            'image_123',
            'description',
            'blob_uri',
            family='sles',
            guest_os_features=['UEFI_COMPATIBLE']
        )

    # Test successful operation
    operation = {}
    mock_wait_on_op.return_value = operation
    create_gce_image(
        driver,
        'project',
        'image_123',
        'description',
        'blob_uri',
        family='sles',
        guest_os_features=['UEFI_COMPATIBLE']
    )


def test_get_gce_image():
    driver = Mock()
    get_op = Mock()
    response = Mock()
    http_resp = Mock()
    http_resp.status = 400
    http_resp.reason = 'Broken'

    driver.images.return_value = get_op
    get_op.get.return_value = response
    response.execute.side_effect = HttpError(http_resp, content=b'Nothing')

    get_gce_image(driver, 'project', 'image name')


@patch('mash.utils.gce.get_gce_image')
def test_deprecate_gce_image(mock_get_gce_image):
    driver = Mock()
    deprecate_op = Mock()
    response = Mock()

    driver.images.return_value = deprecate_op
    deprecate_op.get.return_value = response

    mock_get_gce_image.return_value = {'selfLink': 'link/to/image'}

    deprecate_gce_image(driver, 'project', 'image name', 'replacement name')


@patch('mash.utils.gce.time')
@patch('mash.utils.gce.get_gce_image')
def test_wait_on_image_ready(mock_get_gce_image, mock_time):
    driver = Mock()
    mock_get_gce_image.side_effect = [{}, {'status': 'FAILED'}]

    with raises(MashException):
        wait_on_image_ready(driver, 'project', 'image name')


@patch('mash.utils.gce.discovery')
@patch('mash.utils.gce.service_account')
def test_get_gce_compute_driver(mock_service_account, mock_discovery):
    creds = Mock()
    mock_service_account.Credentials.from_service_account_info.return_value = creds

    get_gce_compute_driver({'some': 'creds'})
    mock_discovery.build.assert_called_once_with(
        'compute',
        'v1',
        credentials=creds,
        cache_discovery=False
    )


@patch('mash.utils.gce.storage')
@patch('mash.utils.gce.service_account')
def test_get_gce_storage_driver(mock_service_account, mock_storage):
    creds = Mock()
    mock_service_account.Credentials.from_service_account_info.return_value = creds

    get_gce_storage_driver({'project_id': 'project'})
    mock_storage.Client.assert_called_once_with('project', creds)


@patch('mash.utils.gce.time')
def test_wait_on_operation(mock_time):
    driver = Mock()
    mock_time.time.return_value = 10

    global_ops_obj = Mock()
    operation = Mock()
    operation.execute.return_value = {'status': 'DONE'}
    global_ops_obj.get.return_value = operation
    driver.globalOperations.return_value = global_ops_obj

    result = wait_on_operation(driver, 'project', 'operation213')
    assert result['status'] == 'DONE'
    assert global_ops_obj.get.call_count == 1

    # Test operation timeout

    mock_time.time.side_effect = [10, 10, 12]
    operation.execute.return_value = {'status': 'PENDING'}

    with raises(MashException):
        wait_on_operation(driver, 'project', 'operation213', timeout=1)
