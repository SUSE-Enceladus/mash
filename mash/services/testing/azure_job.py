# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

from threading import Thread

from mash.services.status_levels import FAILED, SUCCESS
from mash.services.testing.ipa_helper import ipa_test
from mash.services.testing.job import TestingJob


class AzureTestingJob(TestingJob):
    """
    Class for an Azure testing job.
    """
    __test__ = False

    def __init__(
        self, id, provider, ssh_private_key_file, test_regions, tests, utctime,
        job_file=None, credentials=None, description=None, distro='sles',
        instance_type=None, ssh_user='azureuser'
    ):
        super(AzureTestingJob, self).__init__(
            id, provider, ssh_private_key_file, test_regions, tests, utctime,
            job_file=job_file, description=description, distro=distro,
            instance_type=instance_type, ssh_user=ssh_user
        )

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        results = {}
        jobs = []
        for region, account in self.test_regions.items():
            creds = self.credentials[account]
            service_account_credentials = json.dumps(creds)
            process = Thread(
                name=region, target=ipa_test, args=(results,), kwargs={
                    'provider': self.provider,
                    'description': self.description,
                    'distro': self.distro,
                    'image_id': self.source_regions[region],
                    'instance_type': self.instance_type,
                    'region': region,
                    'service_account_credentials': service_account_credentials,
                    'ssh_private_key_file': self.ssh_private_key_file,
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
