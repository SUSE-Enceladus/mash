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

from mash.mash_exceptions import MashJobException
from mash.services.no_op_job import NoOpJob


class BaseJobFactory(object):
    """
    Base Job Factory.
    """
    def __init__(
        self, service_name, job_types, job_type_key=None, can_skip=False
    ):
        self.service_name = service_name
        self.job_types = job_types
        self.job_type_key = job_type_key or 'cloud'
        self.can_skip = can_skip

    def create_job(self, job_config, service_config):
        """
        Create new instance of job based on type,
        """
        job_type = job_config.get(self.job_type_key)

        if not job_type and self.can_skip:
            job_class = NoOpJob
        elif not job_type:
            raise MashJobException('No job type provided, cannot create job.')
        else:
            try:
                job_class = self.job_types[job_type]
            except KeyError:
                raise MashJobException(
                    'Job type {0} is not supported in {1} service.'.format(
                        job_type,
                        self.service_name
                    )
                )

        try:
            job = job_class(job_config, service_config)
        except Exception as error:
            raise MashJobException(
                'Invalid job configuration: {0}'.format(error)
            )

        return job
