# Copyright (c) 2022 SUSE LLC.  All rights reserved.
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

import logging
import os
import random
import traceback

from azure_img_utils.azure_image import AzureImage

from mash.mash_exceptions import MashTestException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.test.utils import process_test_result
from mash.utils.mash_utils import create_ssh_key_pair, create_json_file
from img_proof.ipa_controller import test_image

instance_types = {
    'x86_64': [
        'Standard_B1s',
        'Standard_D2s_v4',
        'Standard_E2s_v4',
        'Standard_F2s_v2'
    ],
    'aarch64': [
        'Standard_D2ps_v5',
        'Standard_E2ps_v5'
    ]
}


class AzureSIGTestJob(MashJob):
    """
    Class for an Azure test job using shared image gallery images.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.container = self.job_config['container']
            self.resource_group = self.job_config['resource_group']
            self.storage_account = self.job_config['storage_account']
            self.tests = self.job_config['tests']
            self.gallery_name = self.job_config['gallery_name']
        except KeyError as error:
            raise MashTestException(
                'Azure test jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'azureuser')
        self.cleanup_images = self.job_config.get('cleanup_images')
        self.cloud_architecture = self.job_config.get(
            'cloud_architecture', 'x86_64'
        )
        self.gallery_resource_group = self.job_config.get(
            'gallery_resource_group'
        ) or self.resource_group

        if not self.instance_type:
            self.instance_type = random.choice(
                instance_types[self.cloud_architecture]
            )

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            create_ssh_key_pair(self.ssh_private_key_file)

    def run_job(self):
        """
        Tests image with img-proof and update status and results.
        """
        self.status = SUCCESS

        if not self.tests:
            self.log_callback.info(
                'Skipping test service, no tests provided.'
            )
            return

        self.log_callback.info(
            'Running img-proof tests against image with '
            'type: {inst_type}.'.format(
                inst_type=self.instance_type
            )
        )

        self.request_credentials([self.account], cloud='azure')
        credentials = self.credentials[self.account]
        self.image_version = self.status_msg['image_version']

        with create_json_file(credentials) as auth_file:
            for image_definition in self.status_msg['images']:
                try:
                    exit_status, result = test_image(
                        'azure',
                        cleanup=True,
                        description=self.description,
                        distro=self.distro,
                        image_id=image_definition,
                        instance_type=self.instance_type,
                        timeout=self.img_proof_timeout,
                        log_level=logging.DEBUG,
                        region=self.region,
                        service_account_file=auth_file,
                        ssh_private_key_file=self.ssh_private_key_file,
                        ssh_user=self.ssh_user,
                        tests=self.tests,
                        log_callback=self.log_callback,
                        prefix_name='mash',
                        gallery_name=self.gallery_name,
                        gallery_resource_group=self.gallery_resource_group,
                        image_version=self.image_version
                    )
                except Exception as error:
                    self.add_error_msg(str(error))
                    exit_status = 1
                    result = {
                        'status': EXCEPTION,
                        'msg': str(traceback.format_exc())
                    }

                self.status = process_test_result(
                    exit_status,
                    result,
                    self.log_callback,
                    self.region,
                    self.status_msg
                )

                if self.status != SUCCESS:
                    break

        if self.status != SUCCESS:
            self.add_error_msg(
                'Image failed img-proof test suite. '
                'See "mash job test-results --job-id {GUID} -v" '
                'for details on the failing tests.'
            )

        if self.cleanup_images or \
                (self.status != SUCCESS and self.cleanup_images is not False):
            self.cleanup_all_images()

    def cleanup_all_images(self):
        credentials = self.credentials[self.account]
        blob_name = self.status_msg['blob_name']

        azure_image = AzureImage(
            container=self.container,
            storage_account=self.storage_account,
            credentials=credentials,
            resource_group=self.gallery_resource_group,
            log_callback=self.log_callback
        )

        for image_definition in self.status_msg['images']:
            self.log_callback.info(
                'Cleaning up image version: {0} of image: {1} '
                'in gallery: {2}.'.format(
                    self.image_version,
                    image_definition,
                    self.gallery_name
                )
            )

            try:
                azure_image.delete_gallery_image_version(
                    self.gallery_name,
                    image_definition,
                    self.image_version
                )
            except Exception as error:
                msg = (
                    'Failed to clean up image version: {0} of image: {1} '
                    'in gallery: {2}. {3}.'.format(
                        self.image_version,
                        image_definition,
                        self.gallery_name,
                        error
                    )
                )
                self.log_callback.warning(msg)
                self.add_error_msg(msg)

        try:
            azure_image.resource_group = self.resource_group
            azure_image.delete_storage_blob(blob_name)
        except Exception as error:
            msg = 'Failed to cleanup image page blob: {0}'.format(error)
            self.log_callback.warning(msg)
            self.add_error_msg(msg)
