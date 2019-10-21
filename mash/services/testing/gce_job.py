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

import json
import os
import random

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS
from mash.services.testing.utils import process_test_result
from mash.utils.mash_utils import create_ssh_key_pair
from mash.utils.gce import cleanup_gce_image
from mash.utils.gce import get_region_list
from mash.services.testing.img_proof_helper import img_proof_test

instance_types = [
    'n1-standard-1',
    'n1-highmem-2',
    'n1-highcpu-2',
    'f1-micro',
]


class GCETestingJob(MashJob):
    """
    Class for an GCE testing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.testing_account = self.job_config['testing_account']
            self.tests = self.job_config['tests']
        except KeyError as error:
            raise MashTestingException(
                'GCE testing jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'root')
        self.cleanup_images = self.job_config.get('cleanup_images')
        self.test_fallback_regions = self.job_config.get('test_fallback_regions')

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
        results = {}
        self.status = SUCCESS
        self.send_log(
            'Running img-proof tests against image with '
            'type: {inst_type}.'.format(
                inst_type=self.instance_type
            )
        )

        accounts = [self.account]
        if self.testing_account:
            # Get both sets of credentials in case cleanup method is run.
            accounts.append(self.testing_account)

        self.request_credentials(accounts)
        creds = self.credentials[self.testing_account or self.account]

        if self.test_fallback_regions == []:
            # fallback testing explicitly disabled
            fallback_regions = []
        else:
            if self.test_fallback_regions is None:
                fallback_regions = get_region_list(creds)
            else:
                fallback_regions = self.test_fallback_regions.copy()
            if self.region in fallback_regions:
                fallback_regions.remove(self.region)

        img_proof_test(
            results,
            cloud=self.cloud,
            description=self.description,
            distro=self.distro,
            fallback_regions=fallback_regions,
            image_id=self.source_regions[self.region],
            instance_type=self.instance_type,
            img_proof_timeout=self.img_proof_timeout,
            region=self.region,
            service_account_credentials=json.dumps(creds),
            ssh_private_key_file=self.ssh_private_key_file,
            ssh_user=self.ssh_user,
            tests=self.tests
        )

        self.status = process_test_result(
            results[self.region],
            self.send_log,
            self.region
        )

        if self.cleanup_images or \
                (self.status != SUCCESS and self.cleanup_images is not False):
            self.cleanup_image()

    def cleanup_image(self):
        credentials = self.credentials[self.account]
        cloud_image_name = self.source_regions[self.region]

        self.send_log(
            'Cleaning up image: {0} in region: {1}.'.format(
                cloud_image_name,
                self.region
            )
        )

        try:
            cleanup_gce_image(credentials, cloud_image_name, self.bucket)
        except Exception as error:
            self.send_log(
                'Failed to cleanup image: {0}'.format(error),
                success=False
            )
