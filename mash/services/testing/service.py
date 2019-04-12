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

from mash.csp import CSP

from mash.services.pipeline_service import PipelineService
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob


class TestingService(PipelineService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud framework and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def service_init(self):
        """
        Initialize testing service class.

        Setup private key file and ipa timeout.
        """
        self.listener_msg_args.append('source_regions')
        self.status_msg_args.append('source_regions')

    def add_job(self, job_config):
        """
        Add job to jobs dict and bind new listener queue to uploader exchange.

        Job description is validated and converted to dict from json.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif cloud == CSP.ec2:
            self._create_job(EC2TestingJob, job_config)
        elif cloud == CSP.azure:
            self._create_job(AzureTestingJob, job_config)
        elif cloud == CSP.gce:
            self._create_job(GCETestingJob, job_config)
        else:
            self.log.error(
                'Cloud {0} is not supported.'.format(cloud)
            )
