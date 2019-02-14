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
from mash.services.deprecation.constants import NOT_IMPLEMENTED


class DeprecationJob(MashJob):
    """
    Class for an individual deprecation job.
    """
    def __init__(
        self, id, last_service, cloud, utctime,
        old_cloud_image_name=None, job_file=None,
        notification_email=None, notification_type='single'
    ):
        super(DeprecationJob, self).__init__(
            id, last_service, cloud, utctime, job_file,
            notification_email=notification_email,
            notification_type=notification_type
        )

        self.old_cloud_image_name = old_cloud_image_name

    def _deprecate(self):
        """
        Deprecate image to all regions in each account.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def process_job(self):
        """
        Deprecate image.
        """
        self.iteration_count += 1
        self._deprecate()
