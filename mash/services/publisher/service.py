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
from mash.services.publisher.azure_job import AzurePublisherJob
from mash.services.publisher.ec2_job import EC2PublisherJob
from mash.services.publisher.gce_job import GCEPublisherJob
from mash.utils.json_format import JsonFormat


class PublisherService(PipelineService):
    """
    Implementation of publisher service.

    Handles the publishing of images in public cloud frameworks.
    """
    def add_job(self, job_config):
        """
        Add new job to publisher queue from job_config.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif cloud == CSP.ec2:
            self._create_job(EC2PublisherJob, job_config)
        elif cloud == CSP.gce:
            self._create_job(GCEPublisherJob, job_config)
        elif cloud == CSP.azure:
            self._create_job(AzurePublisherJob, job_config)
        else:
            self.log.error(
                'Cloud {0} is not supported.'.format(cloud)
            )

    def get_status_message(self, job):
        """
        Build and return json message.

        Message contiains completion status to post to service exchange.
        """
        if job.status == SUCCESS:
            data = {
                'publisher_result': {
                    'id': job.id,
                    'cloud_image_name': job.cloud_image_name,
                    'status': job.status,
                }
            }
        else:
            data = {
                'publisher_result': {
                    'id': job.id,
                    'status': job.status,
                }
            }

        return JsonFormat.json_message(data)
