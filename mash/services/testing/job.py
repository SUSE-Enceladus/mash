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

import dateutil.parser

from mash.mash_exceptions import MashTestingException
from mash.services.status_levels import UNKOWN
from mash.services.testing.constants import NOT_IMPLEMENTED


class TestingJob(object):
    """
    Class for an individual testing job.
    """
    __test__ = False

    def __init__(
        self, id, provider, test_regions, tests, utctime, job_file=None,
        description=None, distro=None, instance_type=None
    ):
        self.cloud_image_name = None
        self.job_file = job_file
        self.credentials = None
        self.description = description
        self.distro = self.validate_distro(distro)
        self.instance_type = instance_type
        self.iteration_count = 0
        self.id = id
        self.log_callback = None
        self.provider = self.validate_provider(provider)
        self.status = UNKOWN
        self.source_regions = None
        self.test_regions = self.validate_test_regions(test_regions)
        self.tests = self.validate_tests(tests)
        self.utctime = self.validate_timestamp(utctime)

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

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

    def validate_distro(self, distro):
        """
        Validate the distro is supported for testing.
        """
        if not distro:
            distro = 'SLES'
        elif distro not in ('openSUSE_Leap', 'SLES'):
            raise MashTestingException(
                'Distro: {0} not supported.'.format(distro)
            )
        return distro

    def validate_provider(self, provider):
        """
        Validate the provider is supported for testing.
        """
        if provider not in ('ec2',):
            raise MashTestingException(
                'Provider: {0} not supported.'.format(provider)
            )
        return provider

    def validate_tests(self, tests):
        """
        Validate the tests attr is a comma separated list of tests.

        There must be at least one test provided.
        """
        try:
            tests = [test for test in filter(None, tests.split(','))]
        except Exception:
            raise MashTestingException(
                'Invalid tests format, must be a comma seperated list.'
            )

        if len(tests) < 1:
            raise MashTestingException(
                'Must provide at least one test.'
            )

        return tests

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

    def validate_timestamp(self, utctime):
        """
        Validate the utctime is always, now or valid utc time format.
        """
        if utctime not in ('always', 'now'):
            try:
                utctime = dateutil.parser.parse(utctime)
            except Exception as e:
                raise MashTestingException(
                    'Invalid utctime format: {0}'.format(e)
                )
        return utctime
