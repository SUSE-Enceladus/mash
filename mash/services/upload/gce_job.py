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

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from mash.utils.gce import get_gce_storage_driver, upload_image_tarball


class GCEUploadJob(MashJob):
    """
    Implements system image upload to GCE
    """
    def post_init(self):
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'GCE upload jobs require a(n) {0} '
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

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]
        storage_driver = get_gce_storage_driver(credentials)

        object_name = ''.join([self.cloud_image_name, '.tar.gz'])
        upload_image_tarball(
            storage_driver,
            object_name,
            self.status_msg['image_file'],
            self.bucket
        )

        self.status_msg['cloud_image_name'] = self.cloud_image_name
        self.status_msg['object_name'] = object_name
        self.log_callback.info(
            'Uploaded image: {0}, to the bucket named: {1}'.format(
                object_name,
                self.bucket
            )
        )
