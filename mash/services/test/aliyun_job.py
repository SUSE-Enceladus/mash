# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

import os
import random
import traceback

from aliyun_img_utils.aliyun_image import AliyunImage

from mash.mash_exceptions import MashTestException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.test.utils import process_test_result
from mash.utils.mash_utils import create_ssh_key_pair
from mash.services.test.img_proof_helper import img_proof_test

instance_types = [
    'ecs.t5-lc1m1.small'
]


class AliyunTestJob(MashJob):
    """
    Class for an Aliyun test job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.tests = self.job_config['tests']
            self.security_group_id = self.job_config['security_group_id']
            self.vswitch_id = self.job_config['vswitch_id']
        except KeyError as error:
            raise MashTestException(
                'Aliyun test jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'ali-user')
        self.cleanup_images = self.job_config.get('cleanup_images')

        if not self.instance_type:
            self.instance_type = random.choice(instance_types)

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            create_ssh_key_pair(self.ssh_private_key_file)

    def run_job(self):
        """
        Tests image with img-proof and update status and results.
        """
        self.status = SUCCESS
        self.log_callback.info(
            'Running img-proof tests against image with '
            'type: {inst_type}.'.format(
                inst_type=self.instance_type
            )
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        self.cloud_image_name = self.status_msg['cloud_image_name']
        self.object_name = self.status_msg['object_name']
        image_id = self.status_msg['source_regions'][self.region]

        try:
            result = img_proof_test(
                cloud='alibaba',  # Different name in img-proof
                access_key=credentials['access_key'],
                access_secret=credentials['access_secret'],
                description=self.description,
                distro=self.distro,
                image_id=image_id,
                instance_type=self.instance_type,
                img_proof_timeout=self.img_proof_timeout,
                region=self.region,
                ssh_private_key_file=self.ssh_private_key_file,
                ssh_user=self.ssh_user,
                tests=self.tests,
                security_group_id=self.security_group_id,
                vswitch_id=self.vswitch_id,
                log_callback=self.log_callback
            )
        except Exception as error:
            self.add_error_msg(str(error))
            result = {
                'status': EXCEPTION,
                'msg': str(traceback.format_exc())
            }

        self.status = process_test_result(
            result,
            self.log_callback,
            self.region,
            self.status_msg
        )

        if self.status != SUCCESS:
            self.add_error_msg(
                'Image failed img-proof test suite. '
                'See "mash job test-results --job-id {GUID} -v" '
                'for details on the failing tests.'
            )

        if self.cleanup_images or \
                (self.status != SUCCESS and self.cleanup_images is not False):
            self.cleanup_image(credentials)

    def cleanup_image(self, credentials):
        aliyun_image = AliyunImage(
            credentials['access_key'],
            credentials['access_secret'],
            self.region,
            self.bucket,
            log_callback=self.log_callback
        )

        self.log_callback.info(
            'Cleaning up image: {0} in region: {1}.'.format(
                self.cloud_image_name,
                self.region
            )
        )

        try:
            aliyun_image.delete_compute_image(self.cloud_image_name)
        except Exception as error:
            msg = 'Failed to cleanup image: {0}'.format(error)
            self.log_callback.warning(msg)
            self.add_error_msg(msg)

        try:
            aliyun_image.delete_storage_blob(self.object_name)
        except Exception as error:
            msg = 'Failed to cleanup image blob: {0}'.format(error)
            self.log_callback.warning(msg)
            self.add_error_msg(msg)
