# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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

import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from mash.csp import CSP

from mash.services.pipeline_service import PipelineService
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob


class TestingService(PipelineService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud framework and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def service_init(self):
        """
        Initialize testing service class.

        Setup private key file and ipa timeout.
        """
        self.listener_msg_args.append('source_regions')
        self.status_msg_args.append('source_regions')
        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.ipa_timeout = self.config.get_ipa_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            self._create_ssh_key_pair()

    def add_job(self, job_config):
        """
        Add job to jobs dict and bind new listener queue to uploader exchange.

        Job description is validated and converted to dict from json.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        job_config['ssh_private_key_file'] = self.ssh_private_key_file
        job_config['ipa_timeout'] = self.ipa_timeout

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif cloud == CSP.ec2:
            self._create_job(EC2TestingJob, job_config)
        elif cloud == CSP.azure:
            self._create_job(AzureTestingJob, job_config)
        elif cloud == CSP.gce:
            self._create_job(GCETestingJob, job_config)
        else:
            self.log.error(
                'Cloud {0} is not supported.'.format(cloud)
            )

    def _create_ssh_key_pair(self):
        """
        Create ssh key pair files based on ssh_private_key_file attribute.
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Get public key
        public_key = private_key.public_key()

        # Write pem formatted private key to file
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(self.ssh_private_key_file, 'wb') as private_key_file:
            private_key_file.write(pem_private_key)

        # Write OpenSSH formatted public key to file
        ssh_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        with open(''.join([self.ssh_private_key_file, '.pub']), 'wb') as public_key_file:
            public_key_file.write(ssh_public_key)
