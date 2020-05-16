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

from oci.retry import RetryStrategyBuilder
from oci.core import ComputeClient, ComputeClientCompositeOperations
from oci.core.models import (
    CreateImageDetails,
    Image,
    ImageSourceViaObjectStorageTupleDetails
)

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashCreateException
from mash.services.status_levels import SUCCESS


class OCICreateJob(MashJob):
    """
    Implements VM image create in OCI.
    """
    def post_init(self):
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.oci_user_id = self.job_config['oci_user_id']
            self.tenancy = self.job_config['tenancy']
            self.compartment_id = self.job_config['compartment_id']
            self.image_description = self.job_config['image_description']
            self.operating_system = self.job_config['operating_system']
            self.operating_system_version = self.job_config['operating_system_version']
        except KeyError as error:
            raise MashCreateException(
                'OCI create jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.image_type = self.job_config.get('image_type', 'QCOW2')
        self.launch_mode = self.job_config.get('launch_mode', 'NATIVE')

        self.max_oci_attempts = self.config.get_max_oci_attempts()
        self.max_oci_wait_seconds = self.config.get_max_oci_wait_seconds()

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Creating image.')

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

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

        object_name = self.source_regions['object_name']
        namespace = self.source_regions['namespace']
        cloud_image_name = self.source_regions['cloud_image_name']

        image_source_details = ImageSourceViaObjectStorageTupleDetails(
            bucket_name=self.bucket,
            namespace_name=namespace,
            object_name=object_name,
            source_image_type=self.image_type,
            operating_system=self.operating_system,
            operating_system_version=self.operating_system_version
        )

        image_details = CreateImageDetails(
            compartment_id=self.compartment_id,
            display_name=cloud_image_name,
            image_source_details=image_source_details,
            launch_mode=self.launch_mode
        )

        retry_strategy = RetryStrategyBuilder(
            max_attempts=self.max_oci_attempts,
            service_error_retry_config={
                'service_error_retry_config': {400: ['LimitExceeded']}
            }
        ).get_retry_strategy()
        response = compute_composite_client.create_image_and_wait_for_state(
            create_image_details=image_details,
            wait_for_states=[
                Image.LIFECYCLE_STATE_AVAILABLE
            ],
            operation_kwargs={'retry_strategy': retry_strategy},
            waiter_kwargs={'max_wait_seconds': self.max_oci_wait_seconds}
        )

        self.source_regions = {
            'cloud_image_name': cloud_image_name,
            'image_id': response.data.id
        }
        self.log_callback.info(
            'Created image has ID: {0}.'.format(
                object_name
            )
        )
