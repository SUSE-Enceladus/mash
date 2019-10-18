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
import random

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.storage.drivers.google_storage import GoogleStorageDriver

from mash.utils.mash_utils import create_json_file


def cleanup_gce_image(credentials, cloud_image_name, bucket):
    """
    Delete the image matching cloud_image_name and the associated tarball.

    Use the provided credentials dict data for authentication.
    """
    with create_json_file(credentials) as auth_file:
        delete_gce_image(credentials, auth_file, cloud_image_name)
        delete_image_tarball(credentials, auth_file, cloud_image_name, bucket)


def delete_image_tarball(credentials, auth_file, cloud_image_name, bucket):
    """
    Delete image tarball based on cloud_image_name from bucket.
    """
    storage_driver = GoogleStorageDriver(
        credentials['client_email'],
        secret=auth_file,
        project=credentials['project_id']
    )

    object_name = ''.join([cloud_image_name, '.tar.gz'])
    image_tarball = storage_driver.get_object(bucket, object_name)
    storage_driver.delete_object(image_tarball)


def delete_gce_image(credentials, auth_file, cloud_image_name):
    """
    Delete the image matching cloud_image_name.
    """
    ComputeEngine = get_driver(Provider.GCE)

    compute_driver = ComputeEngine(
        credentials['client_email'],
        auth_file,
        project=credentials['project_id']
    )
    compute_driver.ex_delete_image(cloud_image_name)


def get_region_list(credentials):
    """
    Returns a list of regions (with random zone suffix) in status UP.

    Use the provided credentials dict data for authentication.
    """
    ComputeEngine = get_driver(Provider.GCE)

    with create_json_file(credentials) as auth_file:
        compute_driver = ComputeEngine(
            credentials['client_email'],
            auth_file,
            project=credentials['project_id']
        )
        regions = compute_driver.ex_list_regions()

    region_names = []
    for region in regions:
        if region.status == 'UP':
            # we actually need a specifc zone not just the region, pick one
            region_names.append(random.choice(region.zones).name)

    return region_names
