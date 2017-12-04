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

from mash.services.testing.job import TestingJob


class EC2TestingJob(TestingJob):
    """
    Class for an EC2 testing job.
    """
    __test__ = False

    def __init__(self,
                 job_id,
                 provider,
                 tests,
                 utctime,
                 account=None,
                 access_key_id=None,
                 desc=None,
                 distro=None,
                 instance_type=None,
                 region=None,
                 secret_access_key=None,
                 ssh_key_name=None,
                 ssh_private_key=None,
                 ssh_user=None):
        super(EC2TestingJob, self).__init__(
            job_id,
            provider,
            tests,
            utctime,
            desc=desc,
            distro=distro,
            instance_type=instance_type,
            region=region
        )
        self.access_key_id = access_key_id
        self.account = account
        self.secret_access_key = secret_access_key
        self.ssh_key_name = ssh_key_name
        self.ssh_private_key = ssh_private_key
        self.ssh_user = ssh_user
