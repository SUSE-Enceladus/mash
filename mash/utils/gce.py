# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

import datetime
import random
import time

from dateutil.relativedelta import relativedelta

from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError

from mash.mash_exceptions import MashException


def upload_image_tarball(storage_driver, object_name, image_file, bucket):
    """
    Upload image tarball to blob in the provided bucket.
    """
    bucket = storage_driver.get_bucket(bucket)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(image_file)


def delete_image_tarball(storage_driver, object_name, bucket):
    """
    Delete image tarball based on object_name from bucket.
    """
    bucket = storage_driver.get_bucket(bucket)
    blob = bucket.blob(object_name)
    blob.delete()


def get_region_list(compute_driver, project):
    """
    Returns a list of regions (with random zone suffix) in status UP.
    """
    regions = compute_driver.regions().list(
        project=project
    ).execute()

    region_names = set()
    for region in regions['items']:
        if region['status'] == 'UP' and region['zones']:
            # we actually need a specific zone not just the region, pick one
            zone = random.choice(region['zones']).split('/')[-1]
            region_names.add(zone)

    return region_names


def create_gce_image(
    compute_driver,
    project,
    cloud_image_name,
    cloud_image_description,
    blob_uri,
    family=None,
    guest_os_features=None
):
    """
    Create a GCE framework image for the blob.

    Wait for create operation to finish and for image
    to be in READY state.
    """
    kwargs = {
        'name': cloud_image_name,
        'description': cloud_image_description,
        'rawDisk': {'source': blob_uri}
    }

    if family:
        kwargs['family'] = family

    if guest_os_features:
        kwargs['guest_os_features'] = guest_os_features

    response = compute_driver.images().insert(
        project=project,
        body=kwargs
    ).execute()

    operation = wait_on_operation(
        compute_driver,
        project,
        response['name']
    )

    if 'error' in operation and operation['error'].get('errors'):
        error = operation['error']['errors'][0]

        raise MashException(
            'Failed to create image: {message}'.format(
                message=error['message']
            )
        )

    wait_on_image_ready(compute_driver, project, cloud_image_name)


def get_gce_image(compute_driver, project, cloud_image_name):
    """
    Retrieve GCE framework image.

    If the image is not found return an empty dictionary.
    """
    try:
        image = compute_driver.images().get(
            project=project,
            image=cloud_image_name
        ).execute()
    except HttpError:
        image = dict()

    return image


def delete_gce_image(compute_driver, project, cloud_image_name):
    """
    Delete the GCE framework image.

    And wait for operation to finish.
    """
    response = compute_driver.images().delete(
        project=project,
        image=cloud_image_name
    ).execute()

    operation = wait_on_operation(
        compute_driver,
        project,
        response['name']
    )

    if 'error' in operation and operation['error'].get('errors'):
        error = operation['error']['errors'][0]

        raise MashException(
            'Failed to delete image: {message}'.format(
                message=error['message']
            )
        )


def deprecate_gce_image(
    compute_driver,
    project,
    cloud_image_name,
    replacement_image_name,
    months_to_deletion=6
):
    """
    Set the image to deprecated.

    Mark it for deletion based on months_to_deletion and
    set the replacement image URI.
    """
    delete_on = datetime.date.today() + relativedelta(
        months=int(months_to_deletion)
    )
    delete_timestamp = ''.join([
        delete_on.isoformat(),
        'T00:00:00.000-00:00'
    ])

    replacement_image = get_gce_image(
        compute_driver,
        project,
        replacement_image_name
    )
    replacement_image_uri = replacement_image['selfLink']

    kwargs = {
        'replacement': replacement_image_uri,
        'deleted': delete_timestamp,
        'state': 'DEPRECATED'
    }

    compute_driver.images().deprecate(
        project=project,
        image=cloud_image_name,
        body=kwargs
    ).execute()


def wait_on_image_ready(compute_driver, project, cloud_image_name):
    """
    Wait for image to be in READY state.

    If image ends up in FAILED state raise an exception.
    """
    status = None

    while status != 'READY':
        image = get_gce_image(compute_driver, project, cloud_image_name)
        status = image.get('status', None)

        if status == 'FAILED':
            raise MashException('Image creation failed.')

        time.sleep(5)


def get_gce_compute_driver(credentials):
    """
    Get an SDK compute driver based on credentials dictionary.

    The credentials dictionary is expected to be a service account.
    """
    client_creds = service_account.Credentials.from_service_account_info(
        credentials
    )

    return discovery.build(
        'compute',
        'v1',
        credentials=client_creds,
        cache_discovery=False
    )


def get_gce_storage_driver(credentials):
    """
    Get an SDK storage driver based on credentials dictionary.

    The credentials dictionary is expected to be a service account.
    """
    project = credentials.get('project_id')
    client_creds = service_account.Credentials.from_service_account_info(
        credentials
    )

    return storage.Client(project, client_creds)


def wait_on_operation(
    compute_driver,
    project,
    operation_name,
    timeout=600,
    wait_period=10
):
    """
    Wait for operation to be in DONE state.

    If operation does not reach the DONE state within the
    timeout period raise an exception.
    """
    start = time.time()
    end = start + timeout

    while time.time() < end:
        time.sleep(wait_period)

        operation = compute_driver.globalOperations().get(
            project=project,
            operation=operation_name
        ).execute()

        if operation['status'] == 'DONE':
            return operation

    raise MashException(
        'Operation did not finish in the allotted time.'
    )
