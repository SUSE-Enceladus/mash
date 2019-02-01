# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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
from mash.services.publisher.constants import NOT_IMPLEMENTED


class PublisherJob(MashJob):
    """
    Class for an individual publisher job.
    """

    def __init__(
        self, id, last_service, cloud, utctime, job_file=None
    ):
        super(PublisherJob, self).__init__(
            id, last_service, cloud, utctime, job_file
        )

    def _publish(self):
        """
        Publish image and update status.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def publish_image(self):
        """
        Update iteration_count and publish image.
        """
        self.iteration_count += 1
        self._publish()
