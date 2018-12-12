# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

from mash.services.replication.azure_utils import (
    copy_blob_to_classic_storage,
    create_auth_file,
    delete_image,
    delete_page_blob
)

from mash.services.replication.job import ReplicationJob
from mash.services.status_levels import FAILED, SUCCESS


class AzureReplicationJob(ReplicationJob):
    """
    Class for an Azure replication job.
    """

    def __init__(
        self, id, image_description, last_service, provider, utctime,
        replication_source_regions, job_file=None
    ):
        super(AzureReplicationJob, self).__init__(
            id, last_service, provider, utctime, job_file=job_file
        )
        self.credentials = None
        self.image_description = image_description
        self.job_file = job_file
        self.replication_source_regions = replication_source_regions

    def _replicate(self):
        """
        Replicate image in each source region.

        The azure replication process requires multiple steps:

        - The image blob is copied from ARM storage to legacy ASM storage
          + The azure publishing process requires an ASM based page blob

        - Once the blob is copied to legacy storage the ARM based image
          and blob are deleted
        """
        self.status = SUCCESS

        for source_region, reg_info in self.replication_source_regions.items():
            credential = self.credentials[reg_info['account']]
            blob_name = ''.join([self.cloud_image_name, '.vhd'])

            with create_auth_file(credential) as auth_file:
                self.send_log(
                    'Copying image for account: {},'
                    ' to classic storage container.'.format(
                        reg_info['account']
                    )
                )

                try:
                    copy_blob_to_classic_storage(
                        auth_file,
                        blob_name,
                        reg_info['source_container'],
                        reg_info['source_resource_group'],
                        reg_info['source_storage_account'],
                        reg_info['destination_container'],
                        reg_info['destination_resource_group'],
                        reg_info['destination_storage_account']
                    )
                    delete_image(
                        auth_file,
                        reg_info['source_resource_group'],
                        self.cloud_image_name
                    )
                    delete_page_blob(
                        auth_file,
                        blob_name,
                        reg_info['source_container'],
                        reg_info['source_resource_group'],
                        reg_info['source_storage_account']
                    )
                except Exception as error:
                    self.send_log(
                        'There was an error copying image blob in {0}:'
                        ' {1}'.format(
                            reg_info['account'], error
                        ),
                        False
                    )
                    self.status = FAILED
