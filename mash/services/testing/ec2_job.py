# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
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

import random

from threading import Thread

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.services.testing.ipa_helper import ipa_test

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
            self.ssh_private_key_file = self.job_config['ssh_private_key_file']
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
        self.ipa_timeout = self.job_config.get('ipa_timeout')
        self.ssh_user = self.job_config.get('ssh_user', 'ec2-user')

        if not self.instance_type:
            self.instance_type = random.choice(instance_types)

    def _run_job(self):
        """
        Tests image with IPA and update status and results.
        """
        results = {}
        jobs = []

        self.status = SUCCESS
        self.send_log('Running IPA tests against image.')

        for region, info in self.test_regions.items():
            if info.get('testing_account'):
                account = info['testing_account']
            else:
                account = info['account']

            creds = self.credentials[account]
            ipa_kwargs = {
                'access_key_id': creds['access_key_id'],
                'cloud': self.cloud,
                'description': self.description,
                'distro': self.distro,
                'image_id': self.source_regions[region],
                'instance_type': self.instance_type,
                'ipa_timeout': self.ipa_timeout,
                'region': region,
                'secret_access_key': creds['secret_access_key'],
                'ssh_private_key_file': self.ssh_private_key_file,
                'ssh_user': self.ssh_user,
                'tests': self.tests
            }

            process = Thread(
                name=region, target=ipa_test,
                args=(results,), kwargs=ipa_kwargs
            )
            process.start()
            jobs.append(process)

        for job in jobs:
            job.join()

        for region, result in results.items():
            if 'results_file' in result:
                self.send_log(
                    'Results file for {0} region: {1}'.format(
                        region, result['results_file']
                    )
                )

            if result['status'] != SUCCESS:
                self.send_log(
                    'Image tests failed in region: {0}.'.format(region),
                    success=False
                )
                if result.get('msg'):
                    self.send_log(result['msg'], success=False)

                self.status = FAILED
