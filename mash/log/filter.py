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
import os


class SchedulerLoggingFilter(logging.Filter):
    def filter(self, record):
        ignore = 'maximum number of running instances reached'
        return ignore not in record.msg


class BaseServiceFilter(logging.Filter):
    """
    Filter rule for BaseService logger

    The message format this filter applies to contains
    two custom fields not part of the standard logging

    * %newline
      will be set to whatever os.linesep is

    * %job
      will be set to job_id or empty if not present
    """
    def filter(self, record):
        record.newline = os.linesep
        if hasattr(record, 'job_id'):
            record.job = 'Job[{0}]: '.format(record.job_id)
        else:
            record.job = ''
        if hasattr(record, 'iteration'):
            record.iteration = 'Pass[{0}]: '.format(record.iteration)
        else:
            record.iteration = ''
        return True
