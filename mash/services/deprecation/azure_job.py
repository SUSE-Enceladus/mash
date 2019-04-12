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

from mash.services.azure_utils import (
    deprecate_image_in_offer_doc,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc
)

from mash.mash_exceptions import MashDeprecationException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS


class AzureDeprecationJob(MashJob):
    """
    Class for an Azure deprecation job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.emails = self.job_config['emails']
            self.offer_id = self.job_config['offer_id']
            self.publisher_id = self.job_config['publisher_id']
            self.sku = self.job_config['sku']
            self.deprecation_regions = self.job_config['deprecation_regions']
        except KeyError as error:
            raise MashDeprecationException(
                'Azure deprecation jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.old_cloud_image_name = self.job_config.get(
            'old_cloud_image_name'
        )
        self.vm_images_key = self.job_config.get('vm_images_key')

    def _run_job(self):
        """
        Update deprecated image in offer doc.

        The deprecated image is no longer shown in gui.
        """
        self.status = SUCCESS

        for account in self.deprecation_regions:
            credential = self.credentials[account]

            self.send_log(
                'Deprecating image for account: {0},'
                ' using cloud partner API.'.format(
                    account
                )
            )

            try:
                offer_doc = request_cloud_partner_offer_doc(
                    credential,
                    self.offer_id,
                    self.publisher_id
                )

                if self.vm_images_key:
                    kwargs = {'vm_images_key': self.vm_images_key}
                else:
                    kwargs = {}

                offer_doc = deprecate_image_in_offer_doc(
                    offer_doc,
                    self.old_cloud_image_name,
                    self.sku,
                    self.send_log,
                    kwargs
                )
                put_cloud_partner_offer_doc(
                    credential,
                    offer_doc,
                    self.offer_id,
                    self.publisher_id
                )
                self.send_log(
                    'Deprecation finished for account: '
                    '{}.'.format(
                        account
                    )
                )
            except Exception as error:
                self.send_log(
                    'There was an error deprecating image in {0}:'
                    ' {1}'.format(
                        account, error
                    ),
                    False
                )
                self.status = FAILED
