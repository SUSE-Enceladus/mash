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

import jwt
import logging

from datetime import datetime, timedelta

from ipa.ipa_controller import test_image

from jwt import ExpiredSignatureError, InvalidTokenError

from mash.mash_exceptions import MashTestingException
from mash.services.testing.job import TestingJob


class EC2TestingJob(TestingJob):
    """
    Class for an EC2 testing job.
    """
    __test__ = False

    def __init__(
        self, distro, id, provider, tests, utctime, account=None,
        access_key_id=None, config_file=None, desc=None, image_id=None,
        image_name=None, instance_type=None, region=None,
        secret_access_key=None, source_region=None, ssh_key_name=None,
        ssh_private_key=None, ssh_user=None
    ):
        super(EC2TestingJob, self).__init__(
            distro, id, provider, tests, utctime,
            config_file=config_file, desc=desc, image_id=image_id,
            instance_type=instance_type, region=region
        )
        self.access_key_id = access_key_id
        self.account = account
        self.image_name = image_name,
        self.secret_access_key = secret_access_key
        self.source_region = source_region
        self.ssh_key_name = ssh_key_name
        self.ssh_private_key = ssh_private_key
        self.ssh_user = ssh_user

    def _get_credential_request(self):
        """
        Return json dictionary with credentials request message.
        """
        request = {
            'exp': datetime.utcnow() + timedelta(minutes=5),
            'iat': datetime.utcnow(),
            'sub': 'testing.get_credentials',
            'service': 'testing',
            'job_id': self.id,
            'credentials': {
                'csp': self.provider,
                'account': self.account
            }
        }
        return jwt.encode(request, 'mash', algorithm='HS256')

    def _process_credentials(self, credentials):
        """
        Verify credential request successful and update self.
        Update instance attrs with credentials.
        """
        try:
            payload = jwt.decode(
                credentials,
                'mash',
                algorithm='HS256'
            )
        except ExpiredSignatureError:
            raise MashTestingException(
                'Token has expired, cannot retrieve credentials.'
            )
        except InvalidTokenError as error:
            raise MashTestingException(
                'Invalid token, cannot retrieve credentials: {0}'.format(error)
            )

        try:
            creds = payload['credentials']
            self.secret_access_key = creds['secret_access_key']
            self.access_key_id = creds['access_key_id']
            self.ssh_key_name = creds['ssh_key_name']
            self.ssh_private_key = creds['ssh_private_key']
        except KeyError:
            raise MashTestingException(
                'Credentials not found in token.'
            )

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        self.status, self.results = test_image(
            self.provider,
            access_key_id=self.access_key_id,
            account=self.account,
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
