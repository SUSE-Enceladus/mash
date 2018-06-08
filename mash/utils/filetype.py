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
import os
import re
import subprocess


class FileType(object):
    """
    map file magic information to type methods
    """
    def __init__(self, file_name):
        self.file_name = file_name
        file_info = subprocess.Popen(
            ['file', file_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.filetype = file_info.communicate()[0].decode()

    def is_xz(self):
        if re.match('.*: XZ compressed', self.filetype):
            return True
        return False

    def basename(self):
        name = os.path.basename(self.file_name)
        if self.is_xz():
            name = re.sub('\.(xz|lzma)$', '', name)
            name = re.sub('\.(tgz|tlz)$', '.tar', name)
        return name
