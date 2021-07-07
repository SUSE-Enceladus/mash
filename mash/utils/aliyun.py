# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from contextlib import contextmanager, suppress
from aliyun_img_utils.aliyun_utils import (
    get_compute_client,
    import_key_pair,
    delete_key_pair
)
from mash.utils.mash_utils import generate_name, get_key_from_file


@contextmanager
def setup_key_pair(
    access_key,
    region,
    access_secret,
    ssh_private_key_file
):
    """
    Create a temporary key pair in Aliyun.
    """
    try:
        key_name = generate_name()
        ssh_public_key = get_key_from_file(ssh_private_key_file + '.pub')

        client = get_compute_client(
            access_key,
            access_secret,
            region
        )
        import_key_pair(
            key_name,
            ssh_public_key,
            client
        )

        yield key_name
    finally:
        with suppress(Exception):
            delete_key_pair(key_name, client)
