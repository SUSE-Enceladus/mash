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

import re

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashCreateException
from mash.utils.mash_utils import format_string_with_date, create_json_file
from mash.services.status_levels import SUCCESS


class GCECreateJob(MashJob):
    """
    Implements create VM image in GCE.
    """
    def post_init(self):
        self.source_regions = {}
        self.cloud_image_name = ''
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

    def run_job(self):
        self.status = SUCCESS
        self.send_log('Creating image.')

        region_info = self.source_regions[self.region]
        self.cloud_image_name = region_info['cloud_image_name']
        object_name = region_info['object_name']

        timestamp = re.findall(r'\d{8}', self.cloud_image_name)[0]
        self.cloud_image_description = format_string_with_date(
            self.base_cloud_image_description,
            timestamp=timestamp
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        with create_json_file(credentials) as auth_file:
            ComputeEngine = get_driver(Provider.GCE)
            compute_driver = ComputeEngine(
                credentials['client_email'],
                auth_file,
                project=credentials['project_id']
            )

            uri = ''.join([
                'https://www.googleapis.com/storage/v1/b/',
                self.bucket,
                '/o/',
                object_name
            ])

            kwargs = {
                'description': self.cloud_image_description,
                'wait_for_completion': True
            }

            if self.family:
                kwargs['family'] = self.family

            if self.guest_os_features:
                kwargs['guest_os_features'] = self.guest_os_features

            compute_driver.ex_create_image(
                self.cloud_image_name,
                uri,
                **kwargs
            )

        self.send_log(
            'Created image has ID: {0}'.format(
                self.cloud_image_name
            )
        )
