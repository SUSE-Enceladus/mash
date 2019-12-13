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

from multiprocessing import Process, SimpleQueue

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from mash.utils.azure import upload_azure_image


class AzureUploaderJob(MashJob):
    """
    Implements system image upload to Azure
    """
    def post_init(self):
        self._image_file = None
        self.source_regions = {}
        self.cloud_image_name = ''

        try:
            self.container = self.job_config['container']
            self.storage_account = self.job_config['storage_account']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'Azure uploader jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.account = self.job_config.get('account')
        self.region = self.job_config.get('region')
        self.resource_group = self.job_config.get('resource_group')
        self.sas_token = self.job_config.get('sas_token')

    def run_job(self):
        self.status = SUCCESS
        self.send_log('Uploading image.')

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name
        )

        blob_name = ''.join([self.cloud_image_name, '.vhd'])

        if self.sas_token:
            # Jobs with sas_tokens are upload only
            self._upload_image(blob_name)
            self.send_log(
                'Uploaded blob: {blob} using sas token.'.format(
                    blob=blob_name
                )
            )
        else:
            self.request_credentials([self.account])
            credentials = self.credentials[self.account]

            self._upload_image(blob_name, credentials)

            self.source_regions[self.region] = self.cloud_image_name
            self.send_log(
                'Uploaded image: {0}, to the container: {1}'.format(
                    blob_name,
                    self.container
                )
            )

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

    def _upload_image(self, blob_name, credentials=None):
        """
        Upload image as a page blob to an ARM container.

        Run upload in a separate process as zero page check
        is CPU intensive. Raise exception if result queue
        is not empty.
        """
        result = SimpleQueue()
        args = (
            blob_name,
            self.container,
            self.image_file,
            self.config.get_azure_max_retry_attempts(),
            self.config.get_azure_max_workers(),
            self.storage_account,
            result,
            credentials,
            self.resource_group,
            self.sas_token
        )
        upload_process = Process(
            target=upload_azure_image,
            args=args
        )
        upload_process.start()
        upload_process.join()

        if result.empty() is False:
            raise MashUploadException(result.get())
