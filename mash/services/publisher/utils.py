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

import asyncio
import concurrent.futures
import boto3

from concurrent.futures import FIRST_EXCEPTION
from mash.mash_exceptions import MashPublisherException


async def replicate(
    loop, access_key_id, image_desc, image_id, image_name,
    secret_access_key, regions, source_region
):
    """
    Attempt to copy source image to all regions provided.

    Each replication occurs in an executor. If any executor
    fails the replication task fails and exception is raised.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

    tasks = [
        loop.run_in_executor(
            executor, copy_image_to_region,
            access_key_id, image_desc, image_id, image_name,
            region, secret_access_key, source_region
        ) for region in regions if region != source_region
    ]

    done, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)

    for task in done:
        task.result()


def copy_image_to_region(
    access_key_id, image_desc, image_id, image_name,
    region, secret_access_key, source_region
):
    """
    If image name does not already exist copy image to region.

    Wait until image is available to return. This can take > 10
    minutes to finish.
    """
    session = get_session(access_key_id, secret_access_key, region)
    client = get_client_from_session(session, 'ec2')

    if not image_exists(client, image_name):
        try:
            new_image = client.copy_image(
                Description=image_desc,
                Name=image_name,
                SourceImageId=image_id,
                SourceRegion=source_region,
            )

            waiter = client.get_waiter('image_available')
            waiter.wait(
                ImageIds=[new_image['ImageId']],
                Filters=[{'Name': 'state', 'Values': ['available']}],
                WaiterConfig={
                    'Delay': 15,
                    'MaxAttempts': 80
                }
            )
        except Exception as e:
            raise MashPublisherException(
                'There was an error replicating image to {0}. {1}'.format(
                    region, e
                )
            )

        return region


def ec2_image_replicate(
    access_key_id, image_desc, image_id, image_name,
    secret_access_key, regions, source_region
):
    """
    Replicate the source image from the source region to all regions supplied.
    """
    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(
            replicate(
                loop,
                access_key_id,
                image_desc,
                image_id,
                image_name,
                secret_access_key,
                regions,
                source_region,
            )
        )
    except Exception:
        raise
    finally:
        if not loop.is_closed:
            loop.close()


def image_exists(client, image_name):
    """
    Determine if image exists given image name.
    """
    images = client.describe_images(Owners=['self'])['Images']
    for image in images:
        if image_name == image.get('Name'):
            return True
    return False


def get_client_from_session(session, endpoint):
    """
    Return client endpoint for given session.
    """
    return session.client(endpoint)


def get_session(access_key_id, secret_access_key, region_name=None):
    """
    Return client session given credentials and optional region_name.
    """
    return boto3.session.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
    )


def get_regions(access_key_id, secret_access_key, region_name):
    """
    Return list of regions given the account partition.
    """
    session = get_session(access_key_id, secret_access_key, region_name)
    client = get_client_from_session(session, 'sts')

    partition = client.get_caller_identity()['Arn'].split(':')[1]
    return session.get_available_regions(
        'ec2',
        partition_name=partition,
    )
