# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

from mash.mash_exceptions import MashTestingException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.services.testing.constants import NOT_IMPLEMENTED
from mash.services.testing.ipa_helper import ipa_test


class TestingJob(MashJob):
    """
    Class for an individual testing job.
    """
    __test__ = False  # Used by pytest to ignore class in auto discovery

    def __init__(
        self, id, last_service, cloud, ssh_private_key_file, test_regions,
        tests, utctime, job_file=None, description=None, distro='sles',
        instance_type=None, ipa_timeout=None, ssh_user=None,
        notification_email=None, notification_type='single'
    ):
        super(TestingJob, self).__init__(
            id, last_service, cloud, utctime, job_file,
            notification_email=notification_email,
            notification_type=notification_type
        )

        # properties
        self._source_regions = None

        self.description = description
        self.distro = distro
        self.instance_type = instance_type
        self.ipa_timeout = ipa_timeout
        self.ssh_private_key_file = ssh_private_key_file
        self.ssh_user = ssh_user
        self.test_regions = self.validate_test_regions(test_regions)
        self.tests = tests

    def _add_cloud_creds(self, creds, ipa_kwargs):
        """
        Update IPA kwargs with cloud credentials.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        results = {}
        jobs = []
        for region, info in self.test_regions.items():
            if info.get('testing_account'):
                account = info['testing_account']
            else:
                account = info['account']

            creds = self.credentials[account]
            ipa_kwargs = {
                'cloud': self.cloud,
                'description': self.description,
                'distro': self.distro,
                'image_id': self.source_regions[region],
                'instance_type': self.instance_type,
                'ipa_timeout': self.ipa_timeout,
                'region': region,
                'ssh_private_key_file': self.ssh_private_key_file,
                'ssh_user': self.ssh_user,
                'tests': self.tests
            }
            ipa_kwargs = self._add_cloud_creds(creds, ipa_kwargs)
            process = Thread(
                name=region, target=ipa_test,
                args=(results,), kwargs=ipa_kwargs
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

    @property
    def source_regions(self):
        """Source regions property."""
        return self._source_regions

    @source_regions.setter
    def source_regions(self, regions):
        """
        Setter for source_regions dictionary.
        """
        self._source_regions = regions

    def process_job(self):
        """
        Get credentials and run image tests with IPA.
        """
        self.iteration_count += 1
        self.send_log('Running IPA tests against image.')
        self._run_tests()

    def validate_test_regions(self, test_regions):
        """
        Ensure the test regions arg is the proper format.

        {'us-east-1': 'test-aws'}

        If format is valid return a dictionary mapping region to
        a dict with account.
        """
        for region, account in test_regions.items():
            if not (region and account):
                raise MashTestingException(
                    'Invalid test_regions format. '
                    'Must be a dict format of {region:account}.'
                )
        return test_regions
