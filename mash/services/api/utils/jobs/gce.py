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


def update_gce_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.
    """
    cloud_account = get_gce_account(
        job_doc['cloud_account'],
        job_doc['requesting_user']
    )

    attrs = [
        'region',
        'bucket',
        'testing_account'
    ]

    for attr in attrs:
        if attr not in job_doc:
            job_doc[attr] = getattr(cloud_account, attr)

    if cloud_account.is_publishing_account and not job_doc.get('family'):
        raise MashJobException(
            'Jobs using a GCE publishing account require a family.'
        )

    if cloud_account.is_publishing_account and not job_doc['testing_account']:
        raise MashJobException(
            'Jobs using a GCE publishing account require'
            ' the use of a testing account.'
        )

    return job_doc
