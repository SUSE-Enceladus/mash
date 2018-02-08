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

import logging

from ipa.ipa_controller import test_image

from mash.mash_exceptions import MashTestingException
from mash.services.testing.job import TestingJob


class EC2TestingJob(TestingJob):
    """
    Class for an EC2 testing job.
    """
    __test__ = False

    def __init__(
        self, id, provider, test_regions, tests, utctime, config_file=None,
        desc=None, distro=None, instance_type=None
    ):
        super(EC2TestingJob, self).__init__(
            id, provider, test_regions, tests, utctime,
            config_file=config_file, desc=desc, distro=distro,
            instance_type=instance_type
        )

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        self.status, results = test_image(
            self.provider,
            access_key_id=None,
            desc=self.desc,
            distro=self.distro,
            image_id=None,
            instance_type=self.instance_type,
            log_level=logging.WARNING,
            region=None,
            secret_access_key=None,
            ssh_key_name=None,
            ssh_private_key=None,
            ssh_user=None,
            tests=self.tests
        )

        if results and results.get('info'):
            if results['info'].get('log_file'):
                self.send_log(
                    'Log file: {0}'.format(results['info']['log_file'])
                )

            if results['info'].get('results_file'):
                self.send_log(
                    'Results file: {0}'.format(
                        results['info']['results_file']
                    )
                )
