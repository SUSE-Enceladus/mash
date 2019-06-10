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

email = {
    'type': 'string',
    'format': 'regex',
    'pattern': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
}

non_empty_string = {
    'type': 'string',
    'minLength': 1
}

utctime = {
    'type': 'string',
    'description': 'An RFC3339 date-time string'
                   '(2019-04-28T06:44:50.142Z)',
    'format': 'regex',
    'pattern': r'^([0-9]+)-(0[1-9]|1[012])-(0[1-9]|[12][0-9]'
               r'|3[01])[Tt]([01][0-9]|2[0-3]):([0-5][0-9]):'
               r'([0-5][0-9]|60)(\.[0-9]+)?(([Zz])|([\+|\-]'
               r'([01][0-9]|2[0-3]):[0-5][0-9]))$'
}
