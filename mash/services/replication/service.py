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
from mash.services.replication.azure_job import AzureReplicationJob
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.gce_job import GCEReplicationJob


class ReplicationService(PipelineService):
    """
    Implementation of replication service.

    Handles the replication of images in public cloud frameworks.
    """
    def service_init(self):
        """
        Initialize replication service class.
        """
        self.listener_msg_args.append('source_regions')

    def add_job(self, job_config):
        """
        Add new job to replication queue from job_config.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif cloud == CSP.ec2:
            self._create_job(EC2ReplicationJob, job_config)
        elif cloud == CSP.azure:
            self._create_job(AzureReplicationJob, job_config)
        elif cloud == CSP.gce:
            self._create_job(GCEReplicationJob, job_config)
        else:
            self.log.error(
                'Cloud {0} is not supported.'.format(cloud)
            )
