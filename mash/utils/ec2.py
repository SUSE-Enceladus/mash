# Copyright (c) 2023 SUSE LLC.  All rights reserved.
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

import os
import re

import boto3

from contextlib import contextmanager, suppress
from mash.utils.mash_utils import generate_name, get_key_from_file
from mash.mash_exceptions import MashEc2UtilsException

from ec2imgutils.ec2setup import EC2Setup
from ec2imgutils.ec2removeimg import EC2RemoveImage


def get_session(access_key_id, secret_access_key, region_name):
    """
    Return session using the given credentials and region.
    """
    return boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name
    )


def get_client(service_name, access_key_id, secret_access_key, region_name):
    """
    Return client session given credentials and region_name.
    """
    session = boto3.session.Session()
    return session.client(
        service_name=service_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
    )


def get_vpc_id_from_subnet(ec2_client, subnet_id):
    response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
    return response['Subnets'][0]['VpcId']


def describe_images(client, image_ids=None, filters=None):
    """
    Return a list of custom images using provided client.

    If image_ids list is provided use it to filter the results.
    """
    kwargs = {'Owners': ['self']}

    if image_ids:
        kwargs['ImageIds'] = image_ids

    if filters:
        kwargs['Filters'] = filters

    images = client.describe_images(**kwargs)['Images']
    return images


@contextmanager
def setup_ec2_networking(
    access_key_id,
    region,
    secret_access_key,
    ssh_private_key_file,
    subnet_id=None
):
    """
    Create a temporary vpc, subnet (unless specified) and security group.

    This provides a security group with an open ssh port.
    """
    try:
        ssh_key_name = generate_name()
        ssh_public_key = get_key_from_file(ssh_private_key_file + '.pub')

        client = get_client(
            'ec2',
            access_key_id,
            secret_access_key,
            region
        )
        client.import_key_pair(
            KeyName=ssh_key_name,
            PublicKeyMaterial=ssh_public_key
        )

        ec2_setup = EC2Setup(
            access_key_id,
            region,
            secret_access_key,
            None,
            False
        )

        if not subnet_id:
            subnet_id = ec2_setup.create_vpc_subnet()
            security_group_id = ec2_setup.create_security_group()
        else:
            vpc_id = get_vpc_id_from_subnet(client, subnet_id)
            security_group_id = ec2_setup.create_security_group(vpc_id=vpc_id)

        yield {
            'ssh_key_name': ssh_key_name,
            'subnet_id': subnet_id,
            'security_group_id': security_group_id
        }
    finally:
        with suppress(Exception):
            client.delete_key_pair(KeyName=ssh_key_name)
            ec2_setup.clean_up()


def wait_for_instance_termination(
    access_key_id,
    instance_id,
    region,
    secret_access_key
):
    client = get_client(
        'ec2',
        access_key_id,
        secret_access_key,
        region
    )
    waiter = client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=[instance_id])


def cleanup_ec2_image(
    access_key_id,
    secret_access_key,
    log_callback,
    region,
    image_id=None,
    image_name=None
):
    log_callback.info(
        'Deleting image: {0} in region: {1}.'.format(
            image_id or image_name,
            region
        )
    )

    kwargs = {
        'access_key': access_key_id,
        'remove_all': True,
        'secret_key': secret_access_key
    }

    if image_id:
        kwargs['image_id'] = image_id
    elif image_name:
        kwargs['image_name'] = image_name
    else:
        raise MashEc2UtilsException(
            'Either image_id or image_name is required '
            'to remove an image.'
        )

    ec2_remove_img = EC2RemoveImage(**kwargs)
    ec2_remove_img.set_region(region)
    ec2_remove_img.remove_images()


def cleanup_all_ec2_images(
    access_key_id,
    secret_access_key,
    log_callback,
    regions,
    image_name
):
    """
    Cleanup the image in every region provided if it exists.
    """
    for region in regions:
        try:
            cleanup_ec2_image(
                access_key_id,
                secret_access_key,
                log_callback,
                region,
                image_name=image_name
            )
        except Exception as error:
            log_callback.warning(
                'Failed to cleanup image: {0}'.format(error)
            )


def get_image(client, cloud_image_name):
    """
    Get image if it exists given image name.
    """
    filters = [{
        'Name': 'name',
        'Values': [
            cloud_image_name,
        ]
    }]
    images = describe_images(client, filters=filters)

    if images and len(images) > 1:
        raise MashEc2UtilsException(
            'Expected only one image but multiple images found'
            f' using the filter {cloud_image_name}.'
        )

    if images:
        return images[0]

    return None


def image_exists(client, cloud_image_name):
    """
    Determine if image exists given image name.
    """
    image = get_image(client, cloud_image_name)

    if image:
        return True
    return False


def get_file_list_from_s3_bucket(
    boto3_session,
    bucket_name,
    filter_regex=None
):
    """Provides the list of files in a bucket
    If a regex is provided in filter_regex parameter, only the matching
    files will be included in the list returned.
    For the file to be included in the returned list, the S3 object name has to
    be a full match for the regex provided.
    """
    s3_client = boto3_session.client(service_name='s3')
    files = []
    if filter_regex:
        regex = re.compile(filter_regex)

    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(Bucket=bucket_name)

    for page in response_iterator:
        for s3_obj in page.get('Contents'):
            file_name = s3_obj['Key']
            if not filter_regex:
                files.append(file_name)
            elif re.fullmatch(regex, file_name):
                files.append(file_name)

    return files


def download_file_from_s3_bucket(
    boto3_session,
    bucket_name,
    obj_key,
    download_path
):
    """Downloads a file from a S3 bucket to the provided directory"""

    download_directory, download_file = os.path.split(download_path)
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)

    s3_client = boto3_session.client(service_name='s3')
    s3_client.download_file(bucket_name, obj_key, download_path)
