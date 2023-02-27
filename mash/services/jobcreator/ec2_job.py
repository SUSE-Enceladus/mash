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
        self.allow_copy = self.kwargs.get('allow_copy', 'none')
        self.billing_codes = self.kwargs.get('billing_codes')
        self.use_root_swap = self.kwargs.get('use_root_swap', False)
        self.tpm_support = self.kwargs.get('tpm_support')
        self.entity_id = self.kwargs.get('entity_id')
        self.version_title = self.kwargs.get('version_title')
        self.release_notes = self.kwargs.get('release_notes')
        self.access_role_arn = self.kwargs.get('access_role_arn')
        self.os_name = self.kwargs.get('os_name')
        self.os_version = self.kwargs.get('os_version')
        self.usage_instructions = self.kwargs.get('usage_instructions')
        self.recommended_instance_type = self.kwargs.get(
            'recommended_instance_type'
        )
        self.publish_in_marketplace = self.kwargs.get(
            'publish_in_marketplace',
            False
        )

    def _get_target_regions_list(self):
        """
        Return list of region info.
        """
        regions = []

        for source_region, value in self.target_account_info.items():
            regions.append(value)

        return regions

    def get_deprecate_message(self):
        """
        Build deprecate job message.
        """
        deprecate_message = {
            'deprecate_job': {
                'cloud': self.cloud,
                'deprecate_regions': self.get_deprecate_regions()
            }
        }
        deprecate_message['deprecate_job'].update(self.base_message)

        if self.old_cloud_image_name:
            deprecate_message['deprecate_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(deprecate_message)

    def get_deprecate_regions(self):
        """
        Return list of deprecate region info.

        """
        return self._get_target_regions_list()

    def get_publish_message(self):
        """
        Build publish job message.
        """
        if self.publish_in_marketplace:
            publish_message = {
                'publish_job': {
                    'cloud': 'ec2_mp',
                    'entity_id': self.entity_id,
                    'version_title': self.version_title,
                    'release_notes': self.release_notes,
                    'access_role_arn': self.access_role_arn,
                    'os_name': self.os_name,
                    'os_version': self.os_version,
                    'usage_instructions': self.usage_instructions,
                    'recommended_instance_type': self.recommended_instance_type,
                    'allow_copy': self.allow_copy,
                    'share_with': self.share_with,
                    'publish_regions': self.get_mp_publish_regions()
                }
            }

            if self.ssh_user:
                publish_message['publish_job']['ssh_user'] = self.ssh_user
        else:
            publish_message = {
                'publish_job': {
                    'cloud': self.cloud,
                    'allow_copy': self.allow_copy,
                    'share_with': self.share_with,
                    'publish_regions': self.get_publish_regions()
                }
            }

        publish_message['publish_job'].update(self.base_message)
        return JsonFormat.json_message(publish_message)

    def get_mp_publish_regions(self):
        """
        Return a dictionary of account names to source region names.
        """
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[value['account']] = source_region

        return target_regions

    def get_publish_regions(self):
        """
        Return a list of publish region info.
        """
        return self._get_target_regions_list()

    def get_replicate_message(self):
        """
        Build replicate job message and publish to replicate exchange.
        """
        replicate_message = {
            'replicate_job': {
                'image_description': self.image_description,
                'cloud': self.cloud,
                'replicate_source_regions':
                    self.get_replicate_source_regions()
            }
        }
        replicate_message['replicate_job'].update(self.base_message)

        return JsonFormat.json_message(replicate_message)

    def get_replicate_source_regions(self):
        """
        Return a dictionary of replicate source regions.
        """
        replicate_source_regions = {}

        for source_region, value in self.target_account_info.items():
            replicate_source_regions[source_region] = {
                'account': value['account'],
                'target_regions': value['target_regions']
            }

        return replicate_source_regions

    def get_test_message(self):
        """
        Build test job message.
        """
        test_message = {
            'test_job': {
                'cloud': self.cloud,
                'tests': self.tests,
                'test_regions': self.get_test_regions(),
            }
        }

        if self.distro:
            test_message['test_job']['distro'] = self.distro

        if self.instance_type:
            test_message['test_job']['instance_type'] = \
                self.instance_type

        if self.ssh_user:
            test_message['test_job']['ssh_user'] = self.ssh_user

        if self.last_service == 'test' and \
                self.cleanup_images in [True, None]:
            test_message['test_job']['cleanup_images'] = True

        elif self.cleanup_images is False:
            test_message['test_job']['cleanup_images'] = False

        if self.test_fallback_regions or self.test_fallback is False:
            test_message['test_job']['test_fallback_regions'] = \
                self.test_fallback_regions

        if self.cloud_architecture:
            test_message['test_job']['cloud_architecture'] = \
                self.cloud_architecture

        test_message['test_job'].update(self.base_message)

        return JsonFormat.json_message(test_message)

    def get_test_regions(self):
        """
        Return a dictionary of target test regions.
        """
        test_regions = {}

        for source_region, value in self.target_account_info.items():
            test_regions[source_region] = {
                'account': value['account'],
                'subnet': value['subnet'],
                'partition': value['partition']
            }

        return test_regions

    def get_create_message(self):
        """
        Build create job message.
        """
        create_message = {
            'create_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'image_description': self.image_description,
                'use_build_time': self.use_build_time,
                'target_regions': self.get_create_regions(),
                'force_replace_image': self.force_replace_image,
                'tpm_support': self.tpm_support,
                'boot_firmware': self.boot_firmware
            }
        }
        create_message['create_job'].update(self.base_message)

        if self.cloud_architecture:
            create_message['create_job']['cloud_architecture'] = \
                self.cloud_architecture

        return JsonFormat.json_message(create_message)

    def get_create_regions(self):
        """
        Return a dictionary of target create regions.
        """
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[source_region] = {
                'account': value['account'],
                'helper_image': value['helper_image'],
                'billing_codes': self.billing_codes,
                'use_root_swap': self.use_root_swap,
                'subnet': value['subnet'],
                'regions': value['target_regions']
            }

        return target_regions

    def get_upload_message(self):
        """
        Build upload job message.
        """
        upload_message = {
            'upload_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'raw_image_upload_type': self.raw_image_upload_type,
                'raw_image_upload_account': self.raw_image_upload_account,
                'raw_image_upload_location': self.raw_image_upload_location,
                'use_build_time': self.use_build_time
            }
        }
        upload_message['upload_job'].update(self.base_message)

        return JsonFormat.json_message(upload_message)
