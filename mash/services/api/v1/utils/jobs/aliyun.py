# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from mash.services.api.v1.utils.accounts.aliyun import get_aliyun_account
from mash.services.api.v1.utils.jobs import validate_job


def validate_aliyun_job(job_doc):
    """
    Validate job.

    And update target_account_info for given job doc.
    """
    job_doc = validate_job(job_doc)

    cloud_account = get_aliyun_account(
        job_doc['cloud_account'],
        job_doc['requesting_user']
    )

    attrs = [
        'region',
        'bucket',
        'security_group_id',
        'vswitch_id'
    ]

    for attr in attrs:
        if attr not in job_doc:
            job_doc[attr] = cloud_account.get(attr)

    return job_doc
