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

from mash.services.replication.job import ReplicationJob
from mash.services.status_levels import SUCCESS


class GCEReplicationJob(ReplicationJob):
    """
    Class for an GCE replication job.
    """

    def __init__(
        self, id, image_description, last_service, provider, utctime,
        replication_source_regions, job_file=None
    ):
        super(GCEReplicationJob, self).__init__(
            id, image_description, last_service, provider, utctime,
            replication_source_regions, job_file=job_file
        )

    def _replicate(self):
        """
        No replication in GCE.
        """
        self.status = SUCCESS
