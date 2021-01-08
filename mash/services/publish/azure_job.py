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
    get_blob_url,
    get_blob_service_with_account_keys,
    publish_cloud_partner_offer,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc,
    update_cloud_partner_offer_doc,
    wait_on_cloud_partner_operation
)

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
            self.image_description = self.job_config['image_description']
            self.label = self.job_config['label']
            self.offer_id = self.job_config['offer_id']
            self.publisher_id = self.job_config['publisher_id']
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
        self.publish_offer = self.job_config.get('publish_offer', False)
        self.generation_id = self.job_config.get('generation_id')
        self.cloud_image_name_generation_suffix = self.job_config.get(
            'cloud_image_name_generation_suffix'
        )

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        self.request_credentials([self.account])
        credential = self.credentials[self.account]

        self.cloud_image_name = self.status_msg['cloud_image_name']
        self.blob_name = self.status_msg['blob_name']

        self.log_callback.info(
            'Publishing image for account: {},'
            ' using cloud partner API.'.format(
                self.account
            )
        )

        try:
            blob_url = self._get_blob_url(
                credential,
                self.blob_name,
                self.container,
                self.resource_group,
                self.storage_account
            )
            offer_doc = request_cloud_partner_offer_doc(
                credential,
                self.offer_id,
                self.publisher_id
            )

            kwargs = {
                'generation_id': self.generation_id,
                'cloud_image_name_generation_suffix': self.cloud_image_name_generation_suffix
            }

            if self.vm_images_key:
                kwargs['vm_images_key'] = self.vm_images_key

            offer_doc = update_cloud_partner_offer_doc(
                offer_doc,
                blob_url,
                self.image_description,
                self.cloud_image_name,
                self.label,
                self.sku,
                **kwargs
            )
            put_cloud_partner_offer_doc(
                credential,
                offer_doc,
                self.offer_id,
                self.publisher_id
            )
            self.log_callback.info(
                'Updated cloud partner offer doc for account: {}.'.format(
                    self.account
                )
            )

            if self.publish_offer:
                operation = publish_cloud_partner_offer(
                    credential,
                    self.offer_id,
                    self.publisher_id
                )
                wait_on_cloud_partner_operation(
                    credential,
                    operation,
                    self.log_callback
                )

            self.log_callback.info(
                'Publishing finished for account: {}.'.format(
                    self.account
                )
            )
        except Exception as error:
            msg = 'There was an error publishing image in {0}: {1}'.format(
                self.account,
                error
            )
            self.add_error_msg(msg)
            self.log_callback.error(msg)
            self.status = FAILED

    @staticmethod
    def _get_blob_url(
        credentials, blob_name, container, resource_group, storage_account
    ):
        """
        Return a SAS url that starts 1 day in past and expires in 92 days.
        """
        blob_service = get_blob_service_with_account_keys(
            credentials,
            resource_group,
            storage_account
        )

        url = get_blob_url(
            blob_service,
            blob_name,
            storage_account,
            container,
            expire_hours=24 * 92,
            start_hours=24
        )

        return url
