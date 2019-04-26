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

import os
import random

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from contextlib import contextmanager, suppress
from string import ascii_lowercase
from tempfile import NamedTemporaryFile

from mash.utils.json_format import JsonFormat


@contextmanager
def create_json_file(data):
    try:
        temp_file = NamedTemporaryFile(delete=False)
        with open(temp_file.name, 'w') as json_file:
            json_file.write(JsonFormat.json_message(data))
        yield temp_file.name
    finally:
        with suppress(OSError):
            os.remove(temp_file.name)


def generate_name(length=8):
    """
    Generate a random lowercase string of the given length: Default of 8.
    """
    return ''.join([random.choice(ascii_lowercase) for i in range(length)])


def get_key_from_file(key_file_path):
    """
    Return a key as string from the given file.
    """
    with open(key_file_path, 'r') as key_file:
        key = key_file.read().strip()

    return key


def create_ssh_key_pair(ssh_private_key_file):
    """
    Create ssh key pair and store in ssh_private_key_file.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Get public key
    public_key = private_key.public_key()

    # Write pem formatted private key to file
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(ssh_private_key_file, 'wb') as private_key_file:
        private_key_file.write(pem_private_key)

    # Write OpenSSH formatted public key to file
    ssh_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )

    with open(''.join([ssh_private_key_file, '.pub']), 'wb') as public_key_file:
        public_key_file.write(ssh_public_key)
