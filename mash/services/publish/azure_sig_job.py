# Copyright (c) 2026 SUSE LLC.  All rights reserved.
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

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS


class AzureSIGPublishJob(MashJob):
    """
    Class for an Azure publishing job using a SIG.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.offer_id = self.job_config['offer_id']
            self.plan_id = self.job_config['sku']
            self.account = self.job_config['account']
            self.resource_group = self.job_config['resource_group']
            self.gallery_name = self.job_config['gallery_name']
            self.container = self.job_config['container']
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

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        accounts = [self.account]

        self.request_credentials(accounts, cloud='azure')
        credential = self.credentials[self.account]

        self.cloud_image_name = self.status_msg['cloud_image_name']

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
                credentials=credential,
                resource_group=self.resource_group,
                log_callback=self.log_callback
            )
            plan_image_name = '_'.join([self.offer_id, self.plan_id]).replace('-', '_')

            kwargs = {
                'version_number': self.status_msg['image_version'],
                'offer_id': self.offer_id,
                'plan_id': self.plan_id,
                'gallery_resource_group': self.resource_group,
                'gallery_name': self.gallery_name,
                'gallery_image_name': plan_image_name,
            }

            if self.vm_images_key:
                kwargs['vm_images_key'] = self.vm_images_key

            azure_image.add_sig_image_to_offer(**kwargs)

            if self.generation_id:
                generation_image_name = '_'.join([self.offer_id, self.generation_id]).replace('-', '_')
                kwargs['generation_id'] = self.generation_id
                kwargs['gallery_image_name'] = generation_image_name
                azure_image.add_sig_image_to_offer(**kwargs)

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
