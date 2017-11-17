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
    @classmethod
    def json_load_byteified(self, file_handle):
        return self._byteify(
            json.load(file_handle, object_hook=self._byteify),
            ignore_dicts=True
        )

    @classmethod
    def json_loads_byteified(self, json_text):
        return self._byteify(
            json.loads(json_text, object_hook=self._byteify),
            ignore_dicts=True
        )

    @classmethod
    def json_message(self, data_dict):
        return json.dumps(
            data_dict, sort_keys=True, indent=4, separators=(',', ': ')
        )

    @classmethod
    def _byteify(self, data, ignore_dicts=False):
        # if this is a unicode string, return its string representation
        if isinstance(data, unicode):
            return data.encode('utf-8')
        # if this is a list of values, return list of byteified values
        if isinstance(data, list):
            return [self._byteify(item, ignore_dicts=True) for item in data]
        # if this is a dictionary, return dictionary of byteified keys
        # and values but only if we haven't already byteified it
        if isinstance(data, dict) and not ignore_dicts:
            return {
                self._byteify(key, ignore_dicts=True): self._byteify(
                    value, ignore_dicts=True
                ) for key, value in data.iteritems()
            }
        # if it's anything else, return it in its original form
        return data
