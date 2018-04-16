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


def get_client(service_name, access_key_id, secret_access_key, region_name):
    """
    Return client session given credentials and region_name.
    """
    return boto3.client(
        service_name=service_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
    )


@contextmanager
def temp_key_pair(
    access_key_id, region, secret_access_key, ssh_private_key_file
):
    """
    Create a temp key pair in the account and region.

    Return the key pair name.
    """
    try:
        key_name = generate_name()
        client = get_client(
            'ec2', access_key_id, secret_access_key, region
        )
        ssh_public_key = get_key_from_file(ssh_private_key_file + '.pub')
        client.import_key_pair(
            KeyName=key_name, PublicKeyMaterial=ssh_public_key
        )
        yield key_name
    finally:
        with suppress(Exception):
            client.delete_key_pair(KeyName=key_name)
