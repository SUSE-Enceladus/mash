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

from mash.utils.azure import (
    copy_blob_to_classic_storage,
    delete_image,
    delete_blob
)

from mash.mash_exceptions import MashReplicateException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.mash_utils import create_json_file


class AzureReplicateJob(MashJob):
    """
    Class for an Azure replicate job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.source_container = self.job_config['source_container']
            self.source_resource_group = self.job_config['source_resource_group']
            self.source_storage_account = self.job_config['source_storage_account']
            self.destination_container = self.job_config['destination_container']
            self.destination_resource_group = self.job_config['destination_resource_group']
            self.destination_storage_account = self.job_config['destination_storage_account']
        except KeyError as error:
            raise MashReplicateException(
                'Azure replicate Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.cleanup_images = self.job_config.get('cleanup_images', True)

    def run_job(self):
        """
        Replicate image in each source region.

        The azure replicate process requires multiple steps:

        - The image blob is copied from ARM storage to legacy ASM storage
          + The azure publishing process requires an ASM based page blob

        - Once the blob is copied to legacy storage the ARM based image
          and blob are deleted
        """
        self.status = SUCCESS

        self.request_credentials([self.account])
        credential = self.credentials[self.account]

        self.cloud_image_name = self.status_msg['cloud_image_name']
        self.blob_name = self.status_msg['blob_name']

        with create_json_file(credential) as auth_file:
            self.log_callback.info(
                'Copying image for account: {},'
                ' to classic storage container.'.format(
                    self.account
                )
            )

            try:
                copy_blob_to_classic_storage(
                    auth_file,
                    self.blob_name,
                    self.source_container,
                    self.source_resource_group,
                    self.source_storage_account,
                    self.destination_container,
                    self.destination_resource_group,
                    self.destination_storage_account,
                    is_page_blob=True
                )

                if self.cleanup_images:
                    self.log_callback.info(
                        'Removing ARM image and page blob for account: {}.'.format(
                            self.account
                        )
                    )
                    delete_image(
                        auth_file,
                        self.source_resource_group,
                        self.cloud_image_name
                    )
                    delete_blob(
                        auth_file,
                        self.blob_name,
                        self.source_container,
                        self.source_resource_group,
                        self.source_storage_account,
                        is_page_blob=True
                    )
            except Exception as error:
                self.log_callback.error(
                    'There was an error copying image blob in {0}: {1}'.format(
                        self.account,
                        error
                    )
                )
                self.status = FAILED
