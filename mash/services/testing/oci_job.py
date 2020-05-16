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

import os
import random
import traceback

from oci.retry import RetryStrategyBuilder
from oci.core import ComputeClient, ComputeClientCompositeOperations
from oci.core.models import Image

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.testing.utils import process_test_result
from mash.utils.mash_utils import create_ssh_key_pair, create_key_file
from mash.services.testing.img_proof_helper import img_proof_test

instance_types = [
    'VM.Standard2.1'
]


class OCITestingJob(MashJob):
    """
    Class for an OCI testing job.
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
            self.oci_user_id = self.job_config['oci_user_id']
            self.tenancy = self.job_config['tenancy']
            self.compartment_id = self.job_config['compartment_id']
            self.availability_domain = self.job_config['availability_domain']
        except KeyError as error:
            raise MashTestingException(
                'OCI testing jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'opc')
        self.cleanup_images = self.job_config.get('cleanup_images')

        if not self.instance_type:
            self.instance_type = random.choice(instance_types)

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()
        self.max_oci_attempts = self.config.get_max_oci_attempts()
        self.max_oci_wait_seconds = self.config.get_max_oci_wait_seconds()

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

        self.cloud_image_name = self.source_regions['cloud_image_name']
        image_id = self.source_regions['image_id']

        with create_key_file(credentials['signing_key']) as signing_key_file:
            try:
                result = img_proof_test(
                    availability_domain=self.availability_domain,
                    cloud=self.cloud,
                    compartment_id=self.compartment_id,
                    description=self.description,
                    distro=self.distro,
                    image_id=image_id,
                    instance_type=self.instance_type,
                    img_proof_timeout=self.img_proof_timeout,
                    oci_user_id=self.oci_user_id,
                    region=self.region,
                    signing_key_file=signing_key_file,
                    signing_key_fingerprint=credentials['fingerprint'],
                    ssh_private_key_file=self.ssh_private_key_file,
                    ssh_user=self.ssh_user,
                    tenancy=self.tenancy,
                    tests=self.tests
                )
            except Exception:
                result = {
                    'status': EXCEPTION,
                    'msg': str(traceback.format_exc())
                }

        self.status = process_test_result(
            result,
            self.log_callback,
            self.region
        )

        if self.cleanup_images or \
                (self.status != SUCCESS and self.cleanup_images is not False):
            self.cleanup_image(credentials, image_id)

    def cleanup_image(self, credentials, image_id):
        self.log_callback.info(
            'Cleaning up image: {0} in region: {1}.'.format(
                self.cloud_image_name,
                self.region
            )
        )

        config = {
            'user': self.oci_user_id,
            'key_content': credentials['signing_key'],
            'fingerprint': credentials['fingerprint'],
            'tenancy': self.tenancy,
            'region': self.region
        }
        compute_client = ComputeClient(config)
        compute_composite_client = ComputeClientCompositeOperations(
            compute_client
        )
        retry_strategy = RetryStrategyBuilder(
            max_attempts=self.max_oci_attempts,
            service_error_retry_config={
                'service_error_retry_config': {400: ['LimitExceeded']}
            }
        ).get_retry_strategy()

        try:
            compute_composite_client.delete_image_and_wait_for_state(
                image_id=image_id,
                wait_for_states=[
                    Image.LIFECYCLE_STATE_DELETED
                ],
                operation_kwargs={'retry_strategy': retry_strategy},
                waiter_kwargs={'max_wait_seconds': self.max_oci_wait_seconds}
            )
        except Exception as error:
            self.log_callback.warning(
                'Failed to cleanup image: {0}'.format(error)
            )
