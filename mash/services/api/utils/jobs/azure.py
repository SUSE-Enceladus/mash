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
from mash.services.api.utils.accounts.azure import get_azure_account
from mash.services.api.utils.jobs import (
    get_services_by_last_service,
    validate_job
)


def validate_azure_job(job_doc):
    """
    Validate job.

    And update target_account_info for given job doc.
    """
    validate_job(job_doc)

    cloud_account = get_azure_account(
        job_doc['cloud_account'],
        job_doc['requesting_user']
    )

    attrs = (
        'region',
        'source_container',
        'source_resource_group',
        'source_storage_account',
        'destination_container',
        'destination_resource_group',
        'destination_storage_account'
    )
    publisher_args = (
        'label',
        'offer_id',
        'publisher_id',
        'sku'
    )

    for attr in attrs:
        if attr not in job_doc:
            job_doc[attr] = getattr(cloud_account, attr)

    services = get_services_by_last_service(job_doc['last_service'])
    if 'publisher' in services:
        for arg in publisher_args:
            if arg not in job_doc:
                raise MashJobException(
                    'Azure publishing jobs require a(n) '
                    ' {arg} argument in the job document.'.format(
                        arg=arg
                    )
                )

    return job_doc
