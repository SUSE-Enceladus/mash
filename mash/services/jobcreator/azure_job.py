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

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class AzureJob(BaseJob):
    """
    Azure job message class.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.emails = self.kwargs['emails']
            self.label = self.kwargs['label']
            self.offer_id = self.kwargs['offer_id']
            self.publisher_id = self.kwargs['publisher_id']
            self.sku = self.kwargs['sku']
        except KeyError as error:
            raise MashJobCreatorException(
                'Azure jobs require a(n) {0} key in the job doc.'.format(
                    error
                )
            )

        self.vm_images_key = self.kwargs.get('vm_images_key')
        self.publish_offer = self.kwargs.get('publish_offer', False)

    def get_deprecation_message(self):
        """
        Build deprecation job message.
        """
        deprecation_message = {
            'deprecation_job': {
                'cloud': self.cloud
            }
        }
        deprecation_message['deprecation_job'].update(self.base_message)

        return JsonFormat.json_message(deprecation_message)

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'emails': self.emails,
                'image_description': self.image_description,
                'label': self.label,
                'offer_id': self.offer_id,
                'cloud': self.cloud,
                'publish_regions': self.get_publisher_regions(),
                'publisher_id': self.publisher_id,
                'sku': self.sku,
                'publish_offer': self.publish_offer
            }
        }

        if self.vm_images_key:
            publisher_message['publisher_job']['vm_images_key'] = \
                self.vm_images_key

        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        publish_regions = []

        for source_region, value in self.target_account_info.items():
            publish_regions.append({
                'account': value['account'],
                'destination_container': value['destination_container'],
                'destination_resource_group':
                    value['destination_resource_group'],
                'destination_storage_account':
                    value['destination_storage_account']
            })

        return publish_regions

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_message = {
            'replication_job': {
                'image_description': self.image_description,
                'cloud': self.cloud,
                'replication_source_regions':
                    self.get_replication_source_regions()
            }
        }
        replication_message['replication_job'].update(self.base_message)

        if self.cleanup_images is not None:
            replication_message['replication_job']['cleanup_images'] = \
                self.cleanup_images

        return JsonFormat.json_message(replication_message)

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.
        """
        return self.target_account_info

    def get_testing_regions(self):
        """
        Return a dictionary of target test regions.
        """
        test_regions = {}

        for source_region, value in self.target_account_info.items():
            test_regions[source_region] = {
                'account': value['account']
            }

        return test_regions

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.
        """
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[source_region] = {}
            target_regions[source_region]['account'] = value['account']
            target_regions[source_region]['container'] = \
                value['source_container']
            target_regions[source_region]['storage_account'] = \
                value['source_storage_account']
            target_regions[source_region]['resource_group'] = \
                value['source_resource_group']

        return target_regions
