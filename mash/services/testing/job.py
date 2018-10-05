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

from mash.mash_exceptions import MashTestingException
from mash.services.status_levels import FAILED, SUCCESS, UNKOWN
from mash.services.testing.constants import NOT_IMPLEMENTED
from mash.services.testing.ipa_helper import ipa_test


class TestingJob(object):
    """
    Class for an individual testing job.
    """
    __test__ = False  # Used by pytest to ignore class in auto discovery

    def __init__(
        self, id, provider, ssh_private_key_file, test_regions, tests, utctime,
        job_file=None, description=None, distro='sles', instance_type=None,
        ssh_user=None
    ):
        self.cloud_image_name = None
        self.job_file = job_file
        self.credentials = None
        self.description = description
        self.distro = distro
        self.instance_type = instance_type
        self.iteration_count = 0
        self.id = id
        self.log_callback = None
        self.provider = provider
        self.status = UNKOWN
        self.source_regions = None
        self.ssh_private_key_file = ssh_private_key_file
        self.ssh_user = ssh_user
        self.test_regions = self.validate_test_regions(test_regions)
        self.tests = tests
        self.utctime = utctime

    def _add_provider_creds(self, creds, ipa_kwargs):
        """
        Update IPA kwargs with provider credentials.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        results = {}
        jobs = []
        for region, account in self.test_regions.items():
            creds = self.credentials[account]
            ipa_kwargs = {
                'provider': self.provider,
                'description': self.description,
                'distro': self.distro,
                'image_id': self.source_regions[region],
                'instance_type': self.instance_type,
                'region': region,
                'ssh_private_key_file': self.ssh_private_key_file,
                'ssh_user': self.ssh_user,
                'tests': self.tests
            }
            ipa_kwargs = self._add_provider_creds(creds, ipa_kwargs)
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

    def get_metadata(self):
        """
        Return dictionary of metadata based on job.
        """
        return {'job_id': self.id}

    def send_log(self, message, success=True):
        """
        Send a log message to the log callback function.
        """
        if self.log_callback:
            self.log_callback(
                'Pass[{0}]: {1}'.format(
                    self.iteration_count,
                    message
                ),
                self.get_metadata(),
                success
            )

    def set_log_callback(self, callback):
        """
        Set log_callback function to callback.
        """
        self.log_callback = callback

    def test_image(self):
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
