# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

from mash.services.api.utils.accounts.oci import get_oci_account
from mash.services.api.utils.jobs import get_services_by_last_service
from mash.mash_exceptions import MashJobException


def update_oci_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.
    """
    user_id = job_doc['requesting_user']
    cloud_account = get_oci_account(job_doc['cloud_account'], user_id)

    attrs = [
        'region',
        'bucket',
        'availability_domain',
        'compartment_id',
        'oci_user_id',
        'tenancy',
    ]
    create_args = [
        'operating_system',
        'operating_system_version'
    ]

    for attr in attrs:
        if attr not in job_doc:
            job_doc[attr] = getattr(cloud_account, attr)

    services = get_services_by_last_service(job_doc['last_service'])

    if 'create' in services:
        for arg in create_args:
            if arg not in job_doc:
                raise MashJobException(
                    'OCI jobs that create an image require an '
                    ' {arg} argument in the job document.'.format(
                        arg=arg
                    )
                )

    return job_doc
