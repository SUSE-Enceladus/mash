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

from mash.services.deprecation.deprecation_job import DeprecationJob
from mash.services.status_levels import FAILED, SUCCESS


class AzureDeprecationJob(DeprecationJob):
    """
    Class for an Azure deprecation job.
    """

    def __init__(
        self, emails, id, last_service, cloud, deprecation_regions, offer_id,
        publisher_id, sku, utctime, old_cloud_image_name, job_file=None,
        notification_email=None, notification_type='single',
        vm_images_key=None
    ):
        super(AzureDeprecationJob, self).__init__(
            id, last_service, cloud, utctime,
            old_cloud_image_name=old_cloud_image_name, job_file=job_file,
            notification_email=notification_email,
            notification_type=notification_type
        )

        self.emails = emails
        self.offer_id = offer_id
        self.publisher_id = publisher_id
        self.deprecation_regions = deprecation_regions
        self.sku = sku
        self.vm_images_key = vm_images_key

    def _deprecate(self):
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
