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
        self.launch_inst_type = self.kwargs.get('launch_inst_type')
        self.cpu_options = self.kwargs.get('cpu_options', {})

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
        if self.publish_in_marketplace:
            deprecate_message = {
                'deprecate_job': {
                    'cloud': 'ec2_mp',
                    'deprecate_regions': self.get_mp_deprecate_regions(),
                    'entity_id': self.entity_id
                }
            }
        else:
            deprecate_message = {
                'deprecate_job': {
                    'cloud': self.cloud,
                    'deprecate_regions': self.get_deprecate_regions(),
                }
            }

        if self.old_cloud_image_name:
            deprecate_message['deprecate_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        deprecate_message['deprecate_job'].update(self.base_message)
        return JsonFormat.json_message(deprecate_message)

    def get_mp_deprecate_regions(self):
        """
        Return a dictionary of account names to source region names.
        """
        target_regions = {}

        for source_region, value in self.target_account_info.items():
            target_regions[value['account']] = source_region

        return target_regions

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
            if not self.old_cloud_image_name:
                publish_message['publish_job']['submit_change_request'] = True
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

        if self.boot_firmware:
            test_message['test_job']['boot_firmware'] = self.boot_firmware

        if self.cpu_options:
            test_message['test_job']['cpu_options'] = self.cpu_options

        test_message['test_job'].update(self.base_message)

        return JsonFormat.json_message(test_message)

    def get_test_regions(self):
        """
        Returns a dictionary of regions for the test service.
        This dictionary will have as key the region name and as value a nested
        dictionary with the following fields:
          - account: which account has to be used for the tests in that region
            This value is extracted from the target_account_info structure
          - partition: which partition this region belongs to. Also extracted
            from the target_account_info struct.
          - subnet: what is the subnet that needs to be used in the tests for
            that region. This data is extracted from the `test_regions` list
            inside the target_account_info dictionary
        """
        regions_for_tests = {}

        for source_region, account_info in self.target_account_info.items():
            for test_region in account_info.get('test_regions', []):
                region_name = test_region['region']
                regions_for_tests[region_name] = {
                    'account': account_info['account'],
                    'partition': account_info['partition'],
                    'subnet': test_region['subnet']
                }
        return regions_for_tests

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
                'boot_firmware': self.boot_firmware,
                'launch_inst_type': self.launch_inst_type
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

    def get_test_preparation_message(self):
        """
        Build test_preparation message.
        """
        image_description = (
            'Image replicated by mash to allow test execution in this region.'
        )
        test_preparation_message = {
            'test_preparation_job': {
                'cloud': self.cloud,
                'cloud_image_name': self.cloud_image_name,
                'replicate_source_regions':
                    self.get_test_preparation_regions(),
                'image_description': image_description,
                'test_preparation': True
            }
        }
        test_preparation_message['test_preparation_job'].update(
            self.base_message
        )

        return JsonFormat.json_message(test_preparation_message)

    def get_test_preparation_regions(self):
        """
        Returns a dictionary of the regions where the test_preparation service
        should replicate the image for the tests.
        """
        test_preparation_regions = {}

        for source_region, value in self.target_account_info.items():
            test_preparation_regions[source_region] = {
                'account': value['account'],
                'target_regions': [],
                'partition': value['partition']
            }
            for test_region in value.get('test_regions', []):
                if test_region['region'] != source_region:
                    test_preparation_regions[source_region]['target_regions']\
                        .append(test_region['region'])

        return test_preparation_regions

    def get_test_cleanup_message(self):
        """
        Build test_cleanup message.
        """
        test_cleanup_message = {
            'test_cleanup_job': {
                'cloud': self.cloud,
                'cloud_image_name': self.cloud_image_name,
                'test_cleanup_regions': self.get_test_preparation_regions()
            }
        }
        test_cleanup_message['test_cleanup_job'].update(self.base_message)

        return JsonFormat.json_message(test_cleanup_message)
