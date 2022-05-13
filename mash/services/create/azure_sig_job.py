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

import re

from datetime import datetime

from azure_img_utils.azure_image import AzureImage

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashCreateException
from mash.services.status_levels import SUCCESS


class AzureSIGCreateJob(MashJob):
    """
    Implements Azure shared image gallery version creation

    Creates a new version inside the image definition based on
    the offer_id, sku and generation_id.

    The format of the image defintion name is: offer_id_sku.
    """
    def post_init(self):
        try:
            self.container = self.job_config['container']
            self.storage_account = self.job_config['storage_account']
            self.resource_group = self.job_config['resource_group']
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.gallery_name = self.job_config['gallery_name']
            self.sku = self.job_config['sku']
            self.offer_id = self.job_config['offer_id']
        except KeyError as error:
            raise MashCreateException(
                'Azure SIG create jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.generation_id = self.job_config.get('generation_id')
        self.gallery_resource_group = self.job_config.get(
            'gallery_resource_group'
        ) or self.resource_group

    def run_job(self):
        self.status = SUCCESS
        self.status_msg['images'] = {}
        self.log_callback.info('Creating image.')

        self.cloud_image_name = self.status_msg['cloud_image_name']
        self.blob_name = self.status_msg['blob_name']

        timestamp = re.findall(r'\d{8}', self.cloud_image_name)[0]
        release_date = datetime.strptime(timestamp, '%Y%m%d').date()
        self.image_version = release_date.strftime("%Y.%m.%d")

        self.request_credentials([self.account], cloud='azure')
        credentials = self.credentials[self.account]

        azure_image = AzureImage(
            container=self.container,
            storage_account=self.storage_account,
            credentials=credentials,
            resource_group=self.resource_group,
            log_callback=self.log_callback
        )

        image_name = self._create_image(
            azure_image,
            plan_id=self.sku
        )
        self.status_msg['images'] = [image_name]

        if self.generation_id:
            image_name = self._create_image(
                azure_image,
                plan_id=self.generation_id
            )
            self.status_msg['images'].append(image_name)

        self.status_msg['image_version'] = self.image_version

    def _create_image(self, azure_image, plan_id):
        """
        Create gallery image version from existing page blob.
        """
        image_name = '_'.join([self.offer_id.replace('-', '_'), plan_id])

        azure_image.create_gallery_image_version(
            blob_name=self.blob_name,
            gallery_name=self.gallery_name,
            gallery_image_name=image_name,
            image_version=self.image_version,
            region=self.region,
            force_replace_image=True
        )

        self.log_callback.info(
            'Created image with version: {0} '
            'in the image defintion: {1} of the gallery: {2} '
            'found in resource group: {3}'.format(
                self.image_version,
                image_name,
                self.gallery_name,
                self.resource_group
            )
        )

        return image_name
