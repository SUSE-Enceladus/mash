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
import json


class JsonFormat(object):
    """
    Helper class to handle unicode characters
    in json formatted messages correctly
    """
    @staticmethod
    def json_load(file_handle):
        return json.load(file_handle)

    @staticmethod
    def json_loads(json_text):
        return json.loads(json_text)

    @staticmethod
    def json_message(data_dict):
        return json.dumps(
            data_dict, sort_keys=True, indent=4, separators=(',', ': ')
        )
