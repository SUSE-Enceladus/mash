# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

import boto3

from contextlib import contextmanager, suppress
from mash.utils.mash_utils import generate_name, get_key_from_file
from mash.mash_exceptions import MashGCEUtilsException

from ec2imgutils.ec2setup import EC2Setup
from ec2imgutils.ec2removeimg import EC2RemoveImage


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


def describe_images(client, image_ids=None):
    """
    Return a list of custom images using provided client.

    If image_ids list is provided use it to filter the results.
    """
    kwargs = {'Owners': ['self']}

    if image_ids:
        kwargs['ImageIds'] = image_ids

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
        'no_confirm': True,
        'remove_all': True,
        'secret_key': secret_access_key
    }

    if image_id:
        kwargs['image_id'] = image_id
    elif image_name:
        kwargs['image_name'] = image_name
    else:
        raise MashGCEUtilsException(
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
    images = describe_images(client)

    for image in images:
        if cloud_image_name == image.get('Name'):
            return image


def image_exists(client, cloud_image_name):
    """
    Determine if image exists given image name.
    """
    image = get_image(client, cloud_image_name)
    if image and cloud_image_name == image.get('Name'):
        return True

    return False
