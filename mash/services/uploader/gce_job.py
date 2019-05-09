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

from tempfile import NamedTemporaryFile

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.storage.drivers.google_storage import GoogleStorageDriver

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date
from mash.utils.json_format import JsonFormat
from mash.services.status_levels import SUCCESS


class GCEUploaderJob(MashJob):
    """
    Implements system image upload to GCE
    """
    def post_init(self):
        self._image_file = None
        self.source_regions = {}
        self.cloud_image_name = ''
        self.cloud_image_description = ''

        try:
            self.target_regions = self.job_config['target_regions']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
            self.base_cloud_image_description = \
                self.job_config['image_description']
        except KeyError as error:
            raise MashUploadException(
                'GCE uploader jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        # SLES 11 is EOL, however images remain available in the
        # build service and thus we need to continue to test for
        # this condition.
        if 'sles-11' in self.base_cloud_image_name:
            raise MashUploadException(
                'No SLES 11 support in mash for GCE.'
            )

    def _run_job(self):
        self.status = SUCCESS
        self.send_log('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )

        timestamp = re.findall(r'\d{8}', self.cloud_image_name)[0]

        self.cloud_image_description = format_string_with_date(
            self.base_cloud_image_description, timestamp=timestamp
        )

        for region, info in self.target_regions.items():
            account = info['account']
            credentials = self.credentials[account]
            self._create_auth_file(credentials)

            storage_driver = GoogleStorageDriver(
                credentials['client_email'],
                secret=self.auth_file.name,
                project=credentials['project_id']
            )

            object_name = ''.join([self.cloud_image_name, '.tar.gz'])
            container = storage_driver.get_container(info['bucket'])

            with open(self.image_file[0], 'rb') as image_stream:
                storage_driver.upload_object_via_stream(
                    image_stream, container, object_name
                )

            ComputeEngine = get_driver(Provider.GCE)
            compute_driver = ComputeEngine(
                credentials['client_email'],
                self.auth_file.name,
                project=credentials['project_id']
            )

            uri = ''.join([
                'https://www.googleapis.com/storage/v1/b/',
                info['bucket'], '/o/', object_name
            ])

            compute_driver.ex_create_image(
                self.cloud_image_name, uri,
                description=self.cloud_image_description,
                family=info['family']
            )
            self.source_regions[region] = self.cloud_image_name
            self.send_log(
                'Uploaded image has ID: {0}'.format(
                    self.cloud_image_name
                )
            )

    def _create_auth_file(self, credentials):
        self.auth_file = NamedTemporaryFile()
        with open(self.auth_file.name, 'w') as gce_auth:
            gce_auth.write(JsonFormat.json_message(credentials))

    @property
    def image_file(self):
        """System image file property."""
        return self._image_file

    @image_file.setter
    def image_file(self, system_image_file):
        """
        Setter for image_file list.
        """
        self._image_file = system_image_file
