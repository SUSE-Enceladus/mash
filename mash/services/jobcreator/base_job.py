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

from mash.utils.json_format import JsonFormat


class BaseJob(object):
    """
    Base job message class.

    Handles incoming job requests.
    """
    def __init__(
        self, accounts_info, cloud_data, job_id, cloud,
        requesting_user, last_service,
        utctime, image, cloud_image_name, image_description, distro,
        download_url, tests, conditions=None, instance_type=None,
        old_cloud_image_name=None, cleanup_images=True,
        cloud_architecture='x86_64', cloud_accounts=None, cloud_groups=None
    ):
        self.id = job_id
        self.accounts_info = accounts_info
        self.cloud_data = cloud_data
        self.cloud = cloud
        self.cloud_accounts = cloud_accounts or []
        self.cloud_groups = cloud_groups or []
        self.requesting_user = requesting_user
        self.last_service = last_service
        self.image = image
        self.cloud_image_name = cloud_image_name
        self.old_cloud_image_name = old_cloud_image_name
        self.image_description = image_description
        self.distro = distro
        self.tests = tests
        self.cleanup_images = cleanup_images
        self.conditions = conditions
        self.download_url = download_url
        self.instance_type = instance_type
        self.cloud_architecture = cloud_architecture
        self.utctime = utctime

        self.base_message = {
            'id': self.id,
            'utctime': self.utctime,
            'last_service': self.last_service
        }

        self.post_init()

    def _get_account_info(self):
        """
        Parse dictionary of account data from accounts file.

        Implementation in child class.
        """
        pass

    def _get_accounts_in_group(self, group, user):
        """
        Return a list of account names given the group name.
        """
        return self.accounts_info['groups'][user][group]

    def get_credentials_message(self):
        """
        Build credentials job message.
        """
        accounts = []
        for source_region, value in self.target_account_info.items():
            accounts.append(value['account'])

        credentials_message = {
            'credentials_job': {
                'cloud': self.cloud,
                'cloud_accounts': accounts,
                'requesting_user': self.requesting_user
            }
        }
        credentials_message['credentials_job'].update(self.base_message)

        return JsonFormat.json_message(credentials_message)

    def get_deprecation_message(self):
        """
        Build deprecation job message.

        Implement in child class.
        """
        pass

    def get_obs_message(self):
        """
        Build OBS job message.
        """
        obs_message = {
            'obs_job': {
                'download_url': self.download_url,
                'image': self.image
            }
        }
        obs_message['obs_job'].update(self.base_message)

        if self.cloud_architecture:
            obs_message['obs_job']['cloud_architecture'] = \
                self.cloud_architecture

        if self.conditions:
            obs_message['obs_job']['conditions'] = self.conditions

        return JsonFormat.json_message(obs_message)

    def get_pint_message(self):
        """
        Build pint job message.
        """
        pint_message = {
            'pint_job': {
                'cloud': self.cloud,
                'cloud_image_name': self.cloud_image_name,
            }
        }
        pint_message['pint_job'].update(self.base_message)

        if self.old_cloud_image_name:
            pint_message['pint_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(pint_message)

    def get_publisher_message(self):
        """
        Build publisher job message.

        Implementation in child class.
        """
        pass

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        pass

    def get_replication_source_regions(self):
        """
        Return a dictionary of replication source regions.

        Implementation in child class.
        """
        pass

    def get_testing_message(self):
        """
        Build testing job message.
        """
        testing_message = {
            'testing_job': {
                'cloud': self.cloud,
                'tests': self.tests,
                'test_regions': self.get_testing_regions()
            }
        }

        if self.distro:
            testing_message['testing_job']['distro'] = self.distro

        if self.instance_type:
            testing_message['testing_job']['instance_type'] = \
                self.instance_type

        testing_message['testing_job'].update(self.base_message)

        return JsonFormat.json_message(testing_message)

    def get_testing_regions(self):
        """
        Return a dictionary of target test regions.

        Implementation in child class.
        """
        pass

    def get_uploader_message(self):
        """
        Build uploader job message.
        """
        uploader_message = {
            'uploader_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'image_description': self.image_description,
                'target_regions': self.get_uploader_regions()
            }
        }
        uploader_message['uploader_job'].update(self.base_message)

        if self.cloud_architecture:
            uploader_message['uploader_job']['cloud_architecture'] = \
                self.cloud_architecture

        return JsonFormat.json_message(uploader_message)

    def get_uploader_regions(self):
        """
        Return a dictionary of target uploader regions.

        Implementation in child class.
        """
        pass

    def post_init(self):
        """
        Post initialization method.

        Implementation in child class.
        """
        pass
