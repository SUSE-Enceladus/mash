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
import distutils


class Defaults(object):
    """
    Default values
    """
    @classmethod
    def get_jobs_dir(self):
        jobs_dir = '/var/tmp/mash/uploader_jobs/'
        distutils.dir_util.mkpath(jobs_dir)
        return jobs_dir

    @classmethod
    def get_config(self):
        return '/etc/mash/uploader_config.yml'

    @classmethod
    def get_log_file(self):
        return '/tmp/uploader_service.log'
