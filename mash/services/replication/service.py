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
from mash.services.status_levels import SUCCESS
from mash.services.replication.azure_job import AzureReplicationJob
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.gce_job import GCEReplicationJob
from mash.utils.json_format import JsonFormat


class ReplicationService(PipelineService):
    """
    Implementation of replication service.

    Handles the replication of images in public cloud frameworks.
    """
    def _add_job(self, job_config):
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

    def _get_status_message(self, job):
        """
        Build and return json message.

        Message contiains completion status to post to service exchange.
        """
        if job.status == SUCCESS:
            data = {
                'replication_result': {
                    'id': job.id,
                    'cloud_image_name': job.cloud_image_name,
                    'status': job.status,
                }
            }
        else:
            data = {
                'replication_result': {
                    'id': job.id,
                    'status': job.status,
                }
            }

        return JsonFormat.json_message(data)

    def _start_job(self, job_id):
        """
        Replicate image for job that matches job_id.
        """
        job = self.jobs[job_id]
        job.replicate_image()

    def _get_listener_msg_args(self):
        """
        Return the required args for the listener message.
        """
        return ['cloud_image_name', 'source_regions']
