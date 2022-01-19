# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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


class OCIJob(BaseJob):
    """
    OCI job message class.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.cloud_account = self.kwargs['cloud_account']
            self.region = self.kwargs['region']
            self.bucket = self.kwargs['bucket']
            self.availability_domain = self.kwargs['availability_domain']
            self.compartment_id = self.kwargs['compartment_id']
            self.oci_user_id = self.kwargs['oci_user_id']
            self.tenancy = self.kwargs['tenancy']
        except KeyError as error:
            raise MashJobCreatorException(
                'OCI jobs require a(n) {0} key in the job doc.'.format(
                    error
                )
            )

        self.image_type = self.kwargs.get('image_type')
        self.launch_mode = self.kwargs.get('launch_mode')
        self.operating_system = self.kwargs.get('operating_system')
        self.operating_system_version = self.kwargs.get(
            'operating_system_version'
        )

    def get_deprecate_message(self):
        """
        Build deprecate job message.
        """
        deprecate_message = {
            'deprecate_job': {
                'cloud': self.cloud,
                'account': self.cloud_account
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
                'distro': self.distro,
                'instance_type': self.instance_type,
                'ssh_user': self.ssh_user,
                'availability_domain': self.availability_domain,
                'compartment_id': self.compartment_id,
                'oci_user_id': self.oci_user_id,
                'tenancy': self.tenancy
            }
        }

        if self.last_service == 'test' and \
                self.cleanup_images in [True, None]:
            test_message['test_job']['cleanup_images'] = True

        elif self.cleanup_images is False:
            test_message['test_job']['cleanup_images'] = False

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
                'availability_domain': self.availability_domain,
                'compartment_id': self.compartment_id,
                'oci_user_id': self.oci_user_id,
                'tenancy': self.tenancy,
                'raw_image_upload_type': self.raw_image_upload_type,
                'raw_image_upload_account': self.raw_image_upload_account,
                'raw_image_upload_location': self.raw_image_upload_location,
                'use_build_time': self.use_build_time
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
                'account': self.cloud_account,
                'bucket': self.bucket,
                'region': self.region,
                'availability_domain': self.availability_domain,
                'compartment_id': self.compartment_id,
                'oci_user_id': self.oci_user_id,
                'tenancy': self.tenancy,
                'operating_system': self.operating_system,
                'operating_system_version': self.operating_system_version
            }
        }
        create_message['create_job'].update(self.base_message)

        if self.image_type:
            create_message['create_job']['image_type'] = self.image_type

        if self.launch_mode:
            create_message['create_job']['launch_mode'] = self.launch_mode

        return JsonFormat.json_message(create_message)
