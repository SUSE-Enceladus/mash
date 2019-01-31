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
