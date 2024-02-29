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

from azure_img_utils.azure_image import AzureImage
from azure_img_utils.storage import get_blob_url

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS


class AzurePublishJob(MashJob):
    """
    Class for an Azure publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.offer_id = self.job_config['offer_id']
            self.sku = self.job_config['sku']
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.container = self.job_config['container']
            self.resource_group = self.job_config['resource_group']
            self.storage_account = self.job_config['storage_account']
        except KeyError as error:
            raise MashPublishException(
                'Azure publish Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.vm_images_key = self.job_config.get('vm_images_key')
        self.generation_id = self.job_config.get('generation_id')
        self.partner_center_account = self.job_config.get('partner_center_account')

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        accounts = [self.account]

        if self.partner_center_account:
            accounts.append(self.partner_center_account)

        self.request_credentials(accounts)
        compute_credential = self.credentials[self.account]

        try:
            pc_credential = self.credentials[self.partner_center_account]
        except KeyError:
            pc_credential = compute_credential

        self.cloud_image_name = self.status_msg['cloud_image_name']
        self.blob_name = self.status_msg['blob_name']

        self.log_callback.info(
            'Adding image to offer for account: {},'
            ' using cloud partner API.'.format(
                self.account
            )
        )

        try:
            azure_image = AzureImage(
                container=self.container,
                storage_account=self.storage_account,
                credentials=compute_credential,
                resource_group=self.resource_group,
                log_callback=self.log_callback
            )
            blob_url = get_blob_url(
                azure_image.blob_service_client,
                self.blob_name,
                self.storage_account,
                self.container,
                expire_hours=24 * 92,
                start_hours=24
            )
        except Exception as error:
            msg = (
                f'There was an error creating a blob url for {self.blob_name}.'
                f' {error}'
            )
            self.add_error_msg(msg)
            self.log_callback.error(msg)
            self.status = FAILED
            return

        try:
            azure_image = AzureImage(
                container=self.container,
                storage_account=self.storage_account,
                credentials=pc_credential,
                resource_group=self.resource_group,
                log_callback=self.log_callback
            )

            kwargs = {
                'blob_name': self.blob_name,
                'image_name': self.cloud_image_name,
                'offer_id': self.offer_id,
                'sku': self.sku,
                'blob_url': blob_url,
                'generation_id': self.generation_id,
            }

            if self.vm_images_key:
                kwargs['vm_images_key'] = self.vm_images_key

            azure_image.add_image_to_offer(**kwargs)

            self.log_callback.info(
                'Updated cloud partner offer doc for account: {}.'.format(
                    self.account
                )
            )
        except Exception as error:
            msg = (
                'There was an error adding image to offer in '
                '{0}: {1}'.format(self.account, error)
            )
            self.add_error_msg(msg)
            self.log_callback.error(msg)
            self.status = FAILED
