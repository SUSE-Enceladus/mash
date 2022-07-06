# Copyright (c) 2022 SUSE LLC.  All rights reserved.
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

import os

from azure_img_utils.azure_image import AzureImage

from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.services.status_levels import SUCCESS


class AzureRawUploadJob(MashJob):
    """
    Implements raw image upload to Azure.

    The image tarball is not expanded during upload.
    """
    def post_init(self):
        try:
            self.container = self.job_config['container']
            self.storage_account = self.job_config['storage_account']
            self.account = self.job_config.get('account')
            self.region = self.job_config.get('region')
            self.resource_group = self.job_config.get('resource_group')
        except KeyError as error:
            raise MashUploadException(
                'Azure raw upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.additional_uploads = self.job_config.get(
            'additional_uploads',
            []
        )

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        self.request_credentials([self.account], 'azure')
        credentials = self.credentials[self.account]

        file_name = self.status_msg['image_file'].rsplit(
            os.sep, maxsplit=1
        )[-1]
        self.additional_uploads.append('')

        azure_image = AzureImage(
            container=self.container,
            storage_account=self.storage_account,
            credentials=credentials,
            resource_group=self.resource_group,
            log_callback=self.log_callback
        )

        for extension in self.additional_uploads:
            upload_file_name = '.'.join(filter(None, [file_name, extension]))
            file_path = '.'.join(
                filter(None, [self.status_msg['image_file'], extension])
            )

            azure_image.upload_image_blob(
                file_path,
                max_workers=self.config.get_azure_max_workers(),
                max_attempts=self.config.get_azure_max_retry_attempts(),
                blob_name=upload_file_name,
                is_page_blob=False,
                expand_image=False
            )

        self.status_msg['blob_name'] = file_name
        self.log_callback.info(
            'Uploaded image: {0}, to the container: {1}'.format(
                file_name,
                self.container
            )
        )
