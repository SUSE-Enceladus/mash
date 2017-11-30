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


class TestingJob(object):
    """
    Class for an individual testing job.
    """
    __test__ = False

    def __init__(self,
                 job_id,
                 provider,
                 tests,
                 utctime,
                 account=None,
                 distro='SLES'):
        self.account = account
        self.distro = distro
        self.image = None
        self.job_id = job_id
        self.log_file = None
        self.provider = self.validate_provider(provider)
        self.results = None
        self.status = None
        self.tests = self.validate_tests(tests)
        self.utctime = self.validate_timestamp(utctime)

    def validate_provider(self, provider):
        """
        Validate the provider is supported for testing.
        """
        if provider not in ('EC2', 'Azure', 'GCE'):
            raise MashTestingException(
                'Provider: {0} not supported.'.format(provider)
            )
        return provider

    def validate_tests(self, tests):
        """
        Valid the tests attr is a comma separated list of tests
        with at least one test.
        """
        try:
            tests = [test for test in filter(None, tests.split(','))]
            assert len(tests)
        except AssertionError:
            raise MashTestingException(
                'Must provide at least one test.'
            )
        except Exception:
            raise MashTestingException(
                'Invalid tests format, must be a comma seperated list.'
            )
        return tests

    def validate_timestamp(self, utctime):
        """
        Validate the utctime is always, now or valid utc time format.
        """
        if utctime not in ('always', 'now'):
            try:
                dateutil.parser.parse(utctime)
            except Exception as e:
                raise MashTestingException(
                    'Invalid utctime format: {0}'.format(e)
                )
        return utctime
