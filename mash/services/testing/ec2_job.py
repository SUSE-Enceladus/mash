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

import os
import random
import traceback

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.testing.utils import (
    get_testing_account,
    process_test_result
)
from mash.utils.mash_utils import create_ssh_key_pair
from mash.utils.ec2 import (
    setup_ec2_networking,
    wait_for_instance_termination
)
from mash.services.testing.img_proof_helper import img_proof_test

instance_types = {
    'x86_64': [
        'c5.large',
        'i3.8xlarge',
        'i3.large',
        'm5.large',
        't3.small'
    ],
    'aarch64': [
        'a1.medium',
        'a1.large'
    ]
}


class EC2TestingJob(MashJob):
    """
    Class for an EC2 testing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.test_regions = self.job_config['test_regions']
            self.tests = self.job_config['tests']
        except KeyError as error:
            raise MashTestingException(
                'EC2 testing jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'ec2-user')
        self.cloud_architecture = self.job_config.get(
            'cloud_architecture', 'x86_64'
        )

        if not self.instance_type:
            self.instance_type = random.choice(
                instance_types[self.cloud_architecture]
            )

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            create_ssh_key_pair(self.ssh_private_key_file)

        self.image_file = None

    def run_job(self):
        """
        Tests image with img-proof and update status and results.
        """
        self.status = SUCCESS
        self.send_log(
            'Running img-proof tests against image with '
            'type: {inst_type}.'.format(
                inst_type=self.instance_type
            )
        )

        # Get all account credentials in one request
        accounts = []
        for region, info in self.test_regions.items():
            accounts.append(get_testing_account(info))

        self.request_credentials(accounts)

        for region, info in self.test_regions.items():
            account = get_testing_account(info)
            credentials = self.credentials[account]

            with setup_ec2_networking(
                credentials['access_key_id'],
                region,
                credentials['secret_access_key'],
                self.ssh_private_key_file,
                subnet_id=info.get('subnet')
            ) as network_details:
                try:
                    result = img_proof_test(
                        access_key_id=credentials['access_key_id'],
                        cloud=self.cloud,
                        description=self.description,
                        distro=self.distro,
                        image_id=self.source_regions[region],
                        instance_type=self.instance_type,
                        img_proof_timeout=self.img_proof_timeout,
                        region=region,
                        secret_access_key=credentials['secret_access_key'],
                        security_group_id=network_details['security_group_id'],
                        ssh_key_name=network_details['ssh_key_name'],
                        ssh_private_key_file=self.ssh_private_key_file,
                        ssh_user=self.ssh_user,
                        subnet_id=network_details['subnet_id'],
                        tests=self.tests
                    )
                except Exception:
                    result = {
                        'status': EXCEPTION,
                        'msg': str(traceback.format_exc())
                    }

                status = process_test_result(result, self.send_log, region)
                if status != SUCCESS:
                    self.status = status

                instance_id = result.get('instance_id')
                if instance_id:
                    # Wait until instance is terminated to exit
                    # context manager and cleanup resources.
                    wait_for_instance_termination(
                        credentials['access_key_id'],
                        instance_id,
                        region,
                        credentials['secret_access_key']
                    )
