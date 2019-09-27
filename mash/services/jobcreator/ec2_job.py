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

from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class EC2Job(BaseJob):
    """
    Base job message class.

    Handles incoming job requests.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        self.share_with = self.kwargs.get('share_with', 'all')
        self.allow_copy = self.kwargs.get('allow_copy', True)
        self.billing_codes = self.kwargs.get('billing_codes')
        self.use_root_swap = self.kwargs.get('use_root_swap', False)

    def _get_target_regions_list(self):
        """
        Return list of region info.
        """
        regions = []

        for source_region, value in self.target_account_info.items():
            regions.append(value)

        return regions

    def get_deprecation_message(self):
        """
        Build deprecation job message.
        """
        deprecation_message = {
            'deprecation_job': {
                'cloud': self.cloud,
                'deprecation_regions': self.get_deprecation_regions()
            }
        }
        deprecation_message['deprecation_job'].update(self.base_message)

        if self.old_cloud_image_name:
            deprecation_message['deprecation_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(deprecation_message)

    def get_deprecation_regions(self):
        """
        Return list of deprecation region info.

        """
        return self._get_target_regions_list()

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'cloud': self.cloud,
                'allow_copy': self.allow_copy,
                'share_with': self.share_with,
                'publish_regions': self.get_publisher_regions()
            }
        }
        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_publisher_regions(self):
        """
        Return a list of publisher region info.
        """
        return self._get_target_regions_list()

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

        return JsonFormat.json_message(replication_message)

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.
        """
        replication_source_regions = {}

        for source_region, value in self.target_account_info.items():
            replication_source_regions[source_region] = {
                'account': value['account'],
                'target_regions': value['target_regions']
            }

        return replication_source_regions

    def get_testing_regions(self):
        """
        Return a dictionary of target test regions.
        """
        test_regions = {}

        for source_region, value in self.target_account_info.items():
            test_regions[source_region] = {
                'account': value['account'],
                'subnet': value['subnet']
            }

        return test_regions

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.
        """
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[source_region] = {
                'account': value['account'],
                'helper_image': value['helper_image'],
                'billing_codes': self.billing_codes,
                'use_root_swap': self.use_root_swap,
                'subnet': value['subnet']
            }

        return target_regions
