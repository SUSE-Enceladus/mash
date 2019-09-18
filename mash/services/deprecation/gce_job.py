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

import datetime

from dateutil.relativedelta import relativedelta

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from mash.mash_exceptions import MashDeprecationException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.mash_utils import create_json_file


class GCEDeprecationJob(MashJob):
    """
    Class for an GCE deprecation job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.deprecation_accounts = self.job_config['deprecation_accounts']
        except KeyError as error:
            raise MashDeprecationException(
                'GCE deprecation Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.months_to_deletion = self.job_config.get('months_to_deletion', 6)
        self.old_cloud_image_name = self.job_config.get(
            'old_cloud_image_name'
        )

    def run_job(self):
        """
        Deprecate image in all accounts.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecation for the job.
            return

        for account in self.deprecation_accounts:
            self.request_credentials([account])
            credential = self.credentials[account]

            with create_json_file(credential) as auth_file:
                try:
                    ComputeEngine = get_driver(Provider.GCE)
                    compute_driver = ComputeEngine(
                        credential['client_email'],
                        auth_file,
                        project=credential['project_id']
                    )

                    delete_on = datetime.date.today() + relativedelta(
                        months=int(self.months_to_deletion)
                    )
                    delete_timestamp = delete_on.isoformat()
                    delete_timestamp += 'T00:00:00.000-00:00'

                    compute_driver.ex_deprecate_image(
                        self.old_cloud_image_name,
                        self.cloud_image_name,
                        deleted=delete_timestamp
                    )
                    self.send_log(
                        'Deprecated image {0}.'.format(
                            self.old_cloud_image_name
                        )
                    )
                except Exception as error:
                    self.send_log(
                        'There was an error deprecating image in {0}:'
                        ' {1}'.format(
                            account, error
                        ),
                        False
                    )
                    self.status = FAILED
