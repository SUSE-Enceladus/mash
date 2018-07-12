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
from lxml import html

from urllib.request import (
    urlretrieve, urlopen, Request
)

from mash.mash_exceptions import MashWebContentException


class WebContent(object):
    """
    Web Content Scanner and Download interface
    """
    def __init__(self, uri):
        self.uri = uri
        self.namespace_map = dict(
            xhtml='http://www.w3.org/1999/xhtml'
        )

    def fetch_index_list(self, base_name):
        try:
            request = Request(self.uri)
            location = urlopen(request)
            tree = html.fromstring(location.read())
            index_list = tree.xpath(
                '//pre/a', namespaces=self.namespace_map
            )
            result = []
            for element in index_list:
                list_entry = element.get('href')
                if list_entry.startswith(base_name):
                    result.append(list_entry)
            return sorted(list(set(result)))
        except Exception as issue:
            raise MashWebContentException(
                '{0}: {1}'.format(type(issue).__name__, issue)
            )

    def fetch_file(self, base_name, suffix, target_file):
        try:
            for name in self.fetch_index_list(base_name):
                if name.startswith(base_name) and name.endswith(suffix):
                    urlretrieve(
                        os.sep.join([self.uri, name]),
                        target_file
                    )
                    return name
        except Exception as issue:
            raise MashWebContentException(
                '{0}: {1}'.format(type(issue).__name__, issue)
            )

    def fetch_files(self, base_name, suffix_list, target_dir):
        try:
            fetched = []
            for name in self.fetch_index_list(base_name):
                if name.startswith(base_name):
                    for suffix in suffix_list:
                        if name.endswith(suffix):
                            target_file = os.sep.join([target_dir, name])
                            urlretrieve(
                                os.sep.join([self.uri, name]),
                                target_file
                            )
                            fetched.append(target_file)
            return fetched
        except Exception as issue:
            raise MashWebContentException(
                '{0}: {1}'.format(type(issue).__name__, issue)
            )
