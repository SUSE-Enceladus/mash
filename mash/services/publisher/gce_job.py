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

from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS


class GCEPublisherJob(MashJob):
    """
    Class for an GCE publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        # Skip credential request since there is no publishing in GCE
        self.credentials = {'status': 'no publishing'}

    def _run_job(self):
        """
        No publishing in GCE.
        """
        self.status = SUCCESS
