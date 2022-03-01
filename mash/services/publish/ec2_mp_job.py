# Copyright (c) 2022 SUSE LLC.  All rights reserved.
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

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS


class EC2MPPublishJob(MashJob):
    """
    Class for an EC2 marketplace publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.publish_regions = self.job_config['publish_regions']
        except KeyError as error:
            raise MashPublishException(
                'EC2 MP publish Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS
