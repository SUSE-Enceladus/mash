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
from mash.services.deprecation.azure_job import AzureDeprecationJob
from mash.services.deprecation.ec2_job import EC2DeprecationJob
from mash.services.deprecation.gce_job import GCEDeprecationJob
from mash.utils.json_format import JsonFormat


class DeprecationService(PipelineService):
    """
    Implementation of deprecation service.

    Deprecates the old image in the given cloud framework for new image.

    * :attr:`custom_args`
    """
    def _add_job(self, job_config):
        """
        Add job to jobs dict and bind new listener queue to publisher exchange.

        Job description is validated and converted to dict from json.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif cloud == CSP.azure:
            self._create_job(AzureDeprecationJob, job_config)
        elif cloud == CSP.ec2:
            self._create_job(EC2DeprecationJob, job_config)
        elif cloud == CSP.gce:
            self._create_job(GCEDeprecationJob, job_config)
        else:
            self.log.exception(
                'Cloud {0} is not supported.'.format(cloud)
            )

    def _get_status_message(self, job):
        """
        Build and return json message with completion status.

        Publish message to service exchange.
        """
        if job.status == SUCCESS:
            data = {
                'deprecation_result': {
                    'id': job.id,
                    'cloud_image_name': job.cloud_image_name,
                    'status': job.status,
                }
            }
        else:
            data = {
                'deprecation_result': {
                    'id': job.id,
                    'status': job.status,
                }
            }

        return JsonFormat.json_message(data)

    def _start_job(self, job_id):
        """
        Deprecate image based on job id.
        """
        job = self.jobs[job_id]
        job.process_job()

    def _get_listener_msg_args(self):
        """
        Return the required args for the listener message.
        """
        return ['cloud_image_name']
