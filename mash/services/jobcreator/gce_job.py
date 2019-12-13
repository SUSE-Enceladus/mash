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
        self.guest_os_features = self.kwargs.get('guest_os_features')

    def get_deprecation_message(self):
        """
        Build deprecation job message.
        """
        deprecation_message = {
            'deprecation_job': {
                'cloud': self.cloud,
                'account': self.cloud_account,
                'months_to_deletion': self.months_to_deletion
            }
        }
        deprecation_message['deprecation_job'].update(self.base_message)

        if self.old_cloud_image_name:
            deprecation_message['deprecation_job']['old_cloud_image_name'] = \
                self.old_cloud_image_name

        return JsonFormat.json_message(deprecation_message)

    def get_publisher_message(self):
        """
        Build publisher job message.
        """
        publisher_message = {
            'publisher_job': {
                'cloud': self.cloud
            }
        }
        publisher_message['publisher_job'].update(self.base_message)

        return JsonFormat.json_message(publisher_message)

    def get_replication_message(self):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_message = {
            'replication_job': {
                'cloud': self.cloud
            }
        }
        replication_message['replication_job'].update(self.base_message)

        return JsonFormat.json_message(replication_message)

    def get_testing_message(self):
        """
        Build testing job message.
        """
        testing_message = {
            'testing_job': {
                'cloud': self.cloud,
                'tests': self.tests,
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region,
                'testing_account': self.testing_account,
                'distro': self.distro,
                'instance_type': self.instance_type
            }
        }

        if self.last_service == 'testing' and \
                self.cleanup_images in [True, None]:
            testing_message['testing_job']['cleanup_images'] = True

        elif self.cleanup_images is False:
            testing_message['testing_job']['cleanup_images'] = False

        if self.test_fallback_regions or self.test_fallback is False:
            testing_message['testing_job']['test_fallback_regions'] = \
                self.test_fallback_regions

        testing_message['testing_job'].update(self.base_message)

        return JsonFormat.json_message(testing_message)

    def get_uploader_message(self):
        """
        Build uploader job message.
        """
        uploader_message = {
            'uploader_job': {
                'cloud_image_name': self.cloud_image_name,
                'cloud': self.cloud,
                'raw_image_upload_type': self.raw_image_upload_type,
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region
            }
        }
        uploader_message['uploader_job'].update(self.base_message)

        return JsonFormat.json_message(uploader_message)

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
