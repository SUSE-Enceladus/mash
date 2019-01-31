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
    create_auth_file,
    get_blob_url,
    get_classic_page_blob_service,
    publish_cloud_partner_offer,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc,
    update_cloud_partner_offer_doc,
    wait_on_cloud_partner_operation
)

from mash.services.publisher.job import PublisherJob
from mash.services.status_levels import FAILED, SUCCESS


class AzurePublisherJob(PublisherJob):
    """
    Class for an Azure publishing job.
    """

    def __init__(
        self, emails, id, image_description, label,
        last_service, offer_id, provider, publish_regions, publisher_id, sku,
        utctime, job_file=None, version_key=None
    ):
        super(AzurePublisherJob, self).__init__(
            id, last_service, provider, utctime, job_file=job_file
        )

        self.emails = emails
        self.image_description = image_description
        self.label = label
        self.offer_id = offer_id
        self.publisher_id = publisher_id
        self.publish_regions = publish_regions
        self.sku = sku
        self.version_key = version_key

    def _publish(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS

        for region_info in self.publish_regions:
            credential = self.credentials[region_info['account']]
            blob_name = ''.join([self.cloud_image_name, '.vhd'])

            with create_auth_file(credential) as auth_file:
                self.send_log(
                    'Publishing image for account: {},'
                    ' using cloud partner API.'.format(
                        region_info['account']
                    )
                )

                try:
                    blob_url = self._get_blob_url(
                        auth_file,
                        blob_name,
                        region_info['destination_container'],
                        region_info['destination_resource_group'],
                        region_info['destination_storage_account']
                    )
                    offer_doc = request_cloud_partner_offer_doc(
                        credential,
                        self.offer_id,
                        self.publisher_id
                    )

                    if self.version_key:
                        kwargs = {'version_key': self.version_key}
                    else:
                        kwargs = {}

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
                    self.send_log(
                        'Updated cloud partner offer doc for account: '
                        '{}.'.format(
                            region_info['account']
                        )
                    )
                    operation = publish_cloud_partner_offer(
                        credential,
                        self.emails,
                        self.offer_id,
                        self.publisher_id
                    )
                    wait_on_cloud_partner_operation(
                        credential,
                        operation,
                        self.send_log
                    )
                    self.send_log(
                        'Publishing finished for account: '
                        '{}.'.format(
                            region_info['account']
                        )
                    )
                except Exception as error:
                    self.send_log(
                        'There was an error publishing image in {0}:'
                        ' {1}'.format(
                            region_info['account'], error
                        ),
                        False
                    )
                    self.status = FAILED

    @staticmethod
    def _get_blob_url(
        auth_file, blob_name, container, resource_group, storage_account
    ):
        """
        Return a SAS url that starts 1 day in past and expires in 3 weeks.
        """
        pbs = get_classic_page_blob_service(
            auth_file,
            resource_group,
            storage_account
        )

        url = get_blob_url(
            pbs,
            blob_name,
            container,
            permissions='rl',
            expire_hours=24 * 21,
            start_hours=24
        )

        return url
