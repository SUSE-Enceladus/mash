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

import os

from cryptography.fernet import Fernet, MultiFernet
from mash.mash_exceptions import MashCredentialsException


def rotate_key(credentials_directory, keys_file, log_callback):
    """
    create a new encryption key and rotate all credentials files.

    Will attempt to rotate credentials files to the new key . If
    any fail an exception is raised prior to return.
    """
    log_callback(
        'Starting key rotation with keys file {0} in directory {1}.'.format(
            keys_file, credentials_directory
        )
    )

    success = True

    # Create new key
    keys = [Fernet.generate_key().decode()]

    # Write both keys to file, new key is first
    with open(keys_file, 'r+') as f:
        keys += [key.strip() for key in f.readlines()]
        f.seek(0)
        f.write('\n'.join(keys))

    fernet_keys = [Fernet(key) for key in keys]
    fernet = MultiFernet(fernet_keys)

    # Rotate all credentials files
    for root, dirs, files in os.walk(credentials_directory):
        for credentials_file in files:
            path = os.path.join(root, credentials_file)

            with open(path, 'r+b') as f:
                credentials = f.read().strip()

                try:
                    credentials = fernet.rotate(credentials)
                except Exception as error:
                    log_callback(
                        'Failed key rotation on credential file {0}:'
                        ' {1}: {2}'.format(
                            path, type(error).__name__, error
                        ),
                        success=False
                    )
                    success = False
                else:
                    f.seek(0)
                    f.write(credentials)

    if not success:
        raise MashCredentialsException(
            'All credentials files have not been rotated.'
        )


def clean_old_keys(keys_file, log_callback):
    """
    Purge old keys from encryption keys file.

    If there's an error send a message to log callback.
    """
    try:
        with open(keys_file, 'r+') as f:
            f.readline()
            f.truncate(f.tell())
    except Exception as error:
        log_callback(
            'Unable to clean old keys from {0}: {1}.'.format(
                keys_file, error
            ),
            success=False
        )
