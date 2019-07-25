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

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS
from mash.services.testing.utils import (
    get_testing_account,
    create_testing_thread,
    process_test_result
)
from mash.utils.mash_utils import create_ssh_key_pair

instance_types = [
    'c5d.large',
    'd2.xlarge',
    'i3.8xlarge',
    'i3.metal',
    'm5.large',
    'm5d.large',
    'r5.24xlarge',
    't2.micro',
    't3.small'
]


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
        jobs = []

        self.status = SUCCESS
        self.send_log('Running img-proof tests against image.')

        for region, info in self.test_regions.items():
            account = get_testing_account(info)
            creds = self.credentials[account]

            img_proof_kwargs = {
                'access_key_id': creds['access_key_id'],
                'cloud': self.cloud,
                'description': self.description,
                'distro': self.distro,
                'image_id': self.source_regions[region],
                'instance_type': self.instance_type,
                'img_proof_timeout': self.img_proof_timeout,
                'region': region,
                'secret_access_key': creds['secret_access_key'],
                'ssh_private_key_file': self.ssh_private_key_file,
                'ssh_user': self.ssh_user,
                'subnet_id': info.get('subnet'),
                'tests': self.tests
            }

            process = create_testing_thread(results, img_proof_kwargs, region)
            jobs.append(process)

        for job in jobs:
            job.join()

        for region, result in results.items():
            status = process_test_result(result, self.send_log, region)
            if status != SUCCESS:
                self.status = status
