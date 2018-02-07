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
        self, id, provider, tests, utctime, config_file=None, desc=None,
        distro=None, instance_type=None
    ):
        super(EC2TestingJob, self).__init__(
            id, provider, tests, utctime, config_file=config_file,
            desc=desc, distro=distro, instance_type=instance_type
        )

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        self.status, self.results = test_image(
            self.provider,
            access_key_id=self.access_key_id,
            desc=self.desc,
            distro=self.distro,
            image_id=self.image_id,
            instance_type=self.instance_type,
            log_level=logging.WARNING,
            region=self.region,
            secret_access_key=self.secret_access_key,
            ssh_key_name=self.ssh_key_name,
            ssh_private_key=self.ssh_private_key,
            ssh_user=self.ssh_user,
            tests=self.tests
        )

        if self.results and self.results.get('info'):
            if self.results['info'].get('log_file'):
                self.send_log(
                    'Log file: {0}'.format(self.results['info']['log_file'])
                )

            if self.results['info'].get('results_file'):
                self.send_log(
                    'Results file: {0}'.format(
                        self.results['info']['results_file']
                    )
                )
