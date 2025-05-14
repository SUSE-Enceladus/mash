# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

import re

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashCreateException
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from gceimgutils.gceutils import get_images_client, get_image
from gceimgutils.gcecreateimg import GCECreateImage
from gceimgutils.gceremoveimg import GCERemoveImage


class GCECreateJob(MashJob):
    """
    Implements create VM image in GCE.
    """
    def post_init(self):
        self.cloud_image_description = ''

        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.base_cloud_image_description = \
                self.job_config['image_description']
        except KeyError as error:
            raise MashCreateException(
                'GCE create jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.family = self.job_config.get('family')
        self.guest_os_features = self.job_config.get('guest_os_features')
        self.arch = self.job_config.get('cloud_architecture', 'x86_64')
        self.skip_rollout = self.job_config.get('skip_rollout', False)

        if self.arch == 'aarch64':
            self.arch = 'arm64'

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Creating image.')

        self.cloud_image_name = self.status_msg['cloud_image_name']
        object_name = self.status_msg['object_name']

        timestamp = re.findall(r'\d{8}', self.cloud_image_name)[0]
        self.cloud_image_description = format_string_with_date(
            self.base_cloud_image_description,
            timestamp=timestamp
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        project = credentials.get('project_id')
        compute_client = get_images_client(credentials)

        if get_image(compute_client, project, self.cloud_image_name):
            self.log_callback.info(
                'Replacing existing image with the same name.'
            )
            remover = GCERemoveImage(
                image_name=self.cloud_image_name,
                credentials_info=credentials,
                project=project,
                log_callback=self.log_callback
            )
            remover.remove_image(self.cloud_image_name)

        # Rollout option is not available in SDK. This can be added
        # back in the future when it becomes available.
        # if self.skip_rollout:
        #     rollout = None
        # else:
        #     rollout = create_gce_rollout(compute_driver, project)

        creator = GCECreateImage(
            self.cloud_image_name,
            self.cloud_image_description,
            self.family,
            self.bucket,
            object_name,
            arch=self.arch,
            guest_os_features=self.guest_os_features,
            credentials_info=credentials,
            project=project,
            log_callback=self.log_callback
        )
        creator.create_image()

        self.log_callback.info(
            'Created image has ID: {0}'.format(
                self.cloud_image_name
            )
        )
