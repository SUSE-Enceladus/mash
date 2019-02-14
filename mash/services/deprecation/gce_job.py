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

from mash.services.deprecation.deprecation_job import DeprecationJob
from mash.services.status_levels import FAILED, SUCCESS
from mash.utils.mash_utils import create_json_file


class GCEDeprecationJob(DeprecationJob):
    """
    Class for an GCE deprecation job.
    """

    def __init__(
        self, id, deprecation_accounts, last_service, cloud, utctime,
        old_cloud_image_name=None, job_file=None, months_to_deletion=6,
        notification_email=None, notification_type='single'
    ):
        super(GCEDeprecationJob, self).__init__(
            id, last_service, cloud, utctime,
            old_cloud_image_name=old_cloud_image_name, job_file=job_file,
            notification_email=notification_email,
            notification_type=notification_type
        )

        self.deprecation_accounts = deprecation_accounts
        self.months_to_deletion = months_to_deletion

    def _deprecate(self):
        """
        Deprecate image in all accounts.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecation for the job.
            return

        for account in self.deprecation_accounts:
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
