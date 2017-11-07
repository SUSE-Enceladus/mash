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
import logging


class SchedulerLoggingFilter(logging.Filter):
    def filter(self, record):
        ignore = 'maximum number of running instances reached'
        return ignore not in record.msg


class JobFilter(logging.Filter):
    """
    Filter mash job logs.

    Only log if msg is json and has keys job_id and msg.

    Expected format:
    '{"job_id": "123", "msg": "Some message..."}'
    """
    def filter(self, record):
        if not hasattr(record, 'job_id'):
            return False
        return True
