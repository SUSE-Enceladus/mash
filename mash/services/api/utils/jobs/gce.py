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

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.accounts.gce import get_gce_account
from mash.services.api.utils.jobs import (
    get_services_by_last_service,
    validate_job
)


def validate_gce_job(job_doc):
    """
    Validate job.

    And update target_account_info for given job doc.
    """
    validate_job(job_doc)

    cloud_account = get_gce_account(
        job_doc['cloud_account'],
        job_doc['requesting_user']
    )

    attrs = [
        'region',
        'bucket',
        'test_account'
    ]

    for attr in attrs:
        if attr not in job_doc:
            job_doc[attr] = getattr(cloud_account, attr)

    services = get_services_by_last_service(job_doc['last_service'])

    if 'create' in services:
        if cloud_account.is_publishing_account and not job_doc.get('family'):
            raise MashJobException(
                'Jobs using a GCE publishing account require a family.'
            )

    if 'test' in services:
        if cloud_account.is_publishing_account and not job_doc['test_account']:
            raise MashJobException(
                'Jobs using a GCE publishing account require'
                ' the use of a test account.'
            )

        if cloud_account.is_publishing_account and not job_doc.get('image_project'):
            raise MashJobException(
                'Jobs using a GCE publishing account require an image_project.'
            )

    return job_doc
