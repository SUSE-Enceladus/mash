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

from mash.services.testing.job import TestingJob

instance_types = [
    'c5d.large',
    'd2.xlarge',
    'h1.2xlarge',
    'i3.8xlarge',
    'i3.metal',
    'm5.large',
    'm5d.large',
    'p3.2xlarge',
    'r5.24xlarge',
    't2.micro',
    't3.small',
    'x1e.xlarge'
]


class EC2TestingJob(TestingJob):
    """
    Class for an EC2 testing job.
    """

    def __init__(
        self, id, provider, ssh_private_key_file, test_regions, tests, utctime,
        job_file=None, credentials=None, description=None, distro='sles',
        instance_type=None, ssh_user='ec2-user'
    ):
        if not instance_type:
            instance_type = random.choice(instance_types)

        super(EC2TestingJob, self).__init__(
            id, provider, ssh_private_key_file, test_regions, tests, utctime,
            job_file=job_file, description=description, distro=distro,
            instance_type=instance_type, ssh_user=ssh_user
        )

    def _add_provider_creds(self, creds, ipa_kwargs):
        """
        Update IPA kwargs with EC2 credentials.
        """
        ipa_kwargs['access_key_id'] = creds['access_key_id']
        ipa_kwargs['secret_access_key'] = creds['secret_access_key']

        return ipa_kwargs
