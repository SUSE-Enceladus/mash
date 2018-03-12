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

from threading import Thread

from mash.services.status_levels import FAILED, SUCCESS
from mash.services.testing.ipa_helper import ipa_test
from mash.services.testing.job import TestingJob


class EC2TestingJob(TestingJob):
    """
    Class for an EC2 testing job.
    """
    __test__ = False

    def __init__(
        self, id, provider, ssh_private_key_file, test_regions, tests, utctime,
        job_file=None, credentials=None, description=None, distro=None,
        instance_type=None, ssh_user='ec2-user'
    ):
        super(EC2TestingJob, self).__init__(
            id, provider, ssh_private_key_file, test_regions, tests, utctime,
            job_file=job_file, description=description, distro=distro,
            instance_type=instance_type
        )
        self.ssh_user = ssh_user

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        results = {}
        jobs = []
        for region, account in self.test_regions.items():
            creds = self.credentials[account]
            process = Thread(
                name=region, target=ipa_test, args=(results,), kwargs={
                    'provider': self.provider,
                    'access_key_id': creds['access_key_id'],
                    'description': self.description,
                    'distro': self.distro,
                    'image_id': self.source_regions[region],
                    'instance_type': self.instance_type,
                    'region': region,
                    'secret_access_key': creds['secret_access_key'],
                    'ssh_private_key': self.ssh_private_key_file,
                    'ssh_user': self.ssh_user,
                    'tests': self.tests
                }
            )
            process.start()
            jobs.append(process)

        for job in jobs:
            job.join()

        self.status = SUCCESS
        for region, result in results.items():
            if result['status'] != SUCCESS:
                self.send_log(
                    'Image tests failed in region: {0}.'.format(region),
                    success=False
                )
                if result.get('msg'):
                    self.send_log(result['msg'], success=False)
                self.status = FAILED
