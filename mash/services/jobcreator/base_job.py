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
from mash.utils.json_format import JsonFormat


class BaseJob(object):
    """
    Base job message class.

    Handles incoming job requests.
    """
    def __init__(self, kwargs):
        try:
            self.id = kwargs['job_id']
            self.cloud = kwargs['cloud']
            self.requesting_user = kwargs['requesting_user']
            self.last_service = kwargs['last_service']
            self.utctime = kwargs['utctime']
            self.image = kwargs['image']
            self.cloud_image_name = kwargs['cloud_image_name']
            self.image_description = kwargs['image_description']
            self.download_url = kwargs['download_url']
        except KeyError as error:
            raise MashJobCreatorException(
                'Jobs require a(n) {0} key in the job doc.'.format(
                    error
                )
            )

        self.tests = kwargs.get('tests', [])
        self.test_fallback_regions = kwargs.get('test_fallback_regions', [])
        self.test_fallback = 'test_fallback_regions' not in kwargs and not self.test_fallback_regions

        self.conditions = kwargs.get('conditions')
        self.distro = kwargs.get('distro')
        self.instance_type = kwargs.get('instance_type')
        self.old_cloud_image_name = kwargs.get('old_cloud_image_name')
        self.cleanup_images = kwargs.get('cleanup_images')
        self.cloud_architecture = kwargs.get('cloud_architecture', 'x86_64')
        self.conditions_wait_time = kwargs.get('conditions_wait_time')
        self.notification_email = kwargs.get('notification_email')
        self.notification_type = kwargs.get('notification_type', 'single')
        self.profile = kwargs.get('profile')
        self.raw_image_upload_type = kwargs.get('raw_image_upload_type')
        self.raw_image_upload_location = kwargs.get('raw_image_upload_location')
        self.raw_image_upload_account = kwargs.get('raw_image_upload_account')
        self.target_account_info = kwargs.get('target_account_info')
        self.disallow_licenses = kwargs.get('disallow_licenses')
        self.disallow_packages = kwargs.get('disallow_packages')
        self.boot_firmware = kwargs.get('boot_firmware', ['bios'])
        self.additional_uploads = kwargs.get('additional_uploads')
        self.kwargs = kwargs

        if self.raw_image_upload_type and self.last_service == 'upload':
            self.cloud = self.raw_image_upload_type

        self.base_message = {
            'id': self.id,
            'utctime': self.utctime,
            'last_service': self.last_service,
            'requesting_user': self.requesting_user
        }

        if self.notification_email:
            self.base_message['notification_email'] = self.notification_email
            self.base_message['notification_type'] = self.notification_type

        self.post_init()

    def get_deprecation_message(self):
        """
        Build deprecation job message.

        Implement in child class.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_deprecation_message method.'.format(
                self.__class__.__name__
            )
        )

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

        if self.profile:
            obs_message['obs_job']['profile'] = self.profile

        if self.conditions_wait_time:
            obs_message['obs_job']['conditions_wait_time'] = \
                self.conditions_wait_time

        if self.disallow_licenses:
            obs_message['obs_job']['disallow_licenses'] = self.disallow_licenses

        if self.disallow_packages:
            obs_message['obs_job']['disallow_packages'] = self.disallow_packages

        return JsonFormat.json_message(obs_message)

    def get_publisher_message(self):
        """
        Build publisher job message.

        Implementation in child class.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_publisher_message method.'.format(
                self.__class__.__name__
            )
        )

    def get_replicate_message(self):
        """
        Build replicate job message and publish to replicate exchange.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_replicate_message method.'.format(
                self.__class__.__name__
            )
        )

    def get_upload_message(self):
        """
        Build upload job message.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_upload_message method.'.format(
                self.__class__.__name__
            )
        )

    def get_test_message(self):
        """
        Build test job message.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_test_message method.'.format(
                self.__class__.__name__
            )
        )

    def get_create_message(self):
        """
        Build create job message.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            'get_create_message method.'.format(
                self.__class__.__name__
            )
        )

    def get_raw_image_upload_message(self):
        """
        Build raw image upload job message.
        """
        raw_image_upload_message = {
            'raw_image_upload_job': {
                'cloud': self.cloud,
                'raw_image_upload_type': self.raw_image_upload_type,
                'raw_image_upload_account': self.raw_image_upload_account,
                'raw_image_upload_location': self.raw_image_upload_location
            }
        }
        raw_image_upload_message['raw_image_upload_job'].update(self.base_message)

        return JsonFormat.json_message(raw_image_upload_message)

    def post_init(self):
        """
        Post initialization method.

        Implementation in child class.
        """
        pass
