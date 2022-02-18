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


class GCEJob(BaseJob):
    """
    GCE job message class.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.cloud_account = self.kwargs['cloud_account']
            self.region = self.kwargs['region']
            self.bucket = self.kwargs['bucket']
            self.testing_account = self.kwargs['testing_account']
        except KeyError as error:
            raise MashJobCreatorException(
                'GCE jobs require a(n) {0} key in the job doc.'.format(
                    error
                )
            )

        self.family = self.kwargs.get('family')
        self.months_to_deletion = self.kwargs.get(
            'months_to_deletion', 6
        )
        self.guest_os_features = self.kwargs.get('guest_os_features', [])
        self.image_project = self.kwargs.get('image_project')

    def get_deprecate_message(self):
        """
        Build deprecate job message.
        """
        deprecate_message = {
            'deprecate_job': {
                'cloud': self.cloud,
                'account': self.cloud_account,
                'months_to_deletion': self.months_to_deletion
            }
        }
        deprecate_message['deprecate_job'].update(self.base_message)

        if self.old_cloud_image_name:
            deprecate_message['deprecate_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(deprecate_message)

    def get_publish_message(self):
        """
        Build publish job message.
        """
        publish_message = {
            'publish_job': {
                'cloud': self.cloud
            }
        }
        publish_message['publish_job'].update(self.base_message)

        return JsonFormat.json_message(publish_message)

    def get_replicate_message(self):
        """
        Build replicate job message and publish to replicate exchange.
        """
        replicate_message = {
            'replicate_job': {
                'cloud': self.cloud
            }
        }
        replicate_message['replicate_job'].update(self.base_message)

        return JsonFormat.json_message(replicate_message)

    def get_test_message(self):
        """
        Build test job message.
        """
        test_message = {
            'test_job': {
                'cloud': self.cloud,
                'tests': self.tests,
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region,
                'testing_account': self.testing_account,
                'distro': self.distro,
                'instance_type': self.instance_type,
                'ssh_user': self.ssh_user,
                'boot_firmware': self.boot_firmware,
                'guest_os_features': self.guest_os_features
            }
        }

        if self.last_service == 'test' and \
                self.cleanup_images in [True, None]:
            test_message['test_job']['cleanup_images'] = True

        elif self.cleanup_images is False:
            test_message['test_job']['cleanup_images'] = False

        if self.test_fallback_regions or self.test_fallback is False:
            test_message['test_job']['test_fallback_regions'] = \
                self.test_fallback_regions

        if self.image_project:
            test_message['test_job']['image_project'] = \
                self.image_project

        test_message['test_job'].update(self.base_message)

        return JsonFormat.json_message(test_message)

    def get_upload_message(self):
        """
        Build upload job message.
        """
        upload_message = {
            'upload_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region,
                'raw_image_upload_type': self.raw_image_upload_type,
                'raw_image_upload_account': self.raw_image_upload_account,
                'raw_image_upload_location': self.raw_image_upload_location,
                'use_build_time': self.use_build_time,
                'force_replace_image': self.force_replace_image
            }
        }
        upload_message['upload_job'].update(self.base_message)

        return JsonFormat.json_message(upload_message)

    def get_create_message(self):
        """
        Build create job message.
        """
        create_message = {
            'create_job': {
                'cloud': self.cloud,
                'image_description': self.image_description,
                'family': self.family,
                'guest_os_features': self.guest_os_features,
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region
            }
        }
        create_message['create_job'].update(self.base_message)

        return JsonFormat.json_message(create_message)
