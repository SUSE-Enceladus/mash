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
from mash.services.api.utils.users import get_user_by_username
from mash.services.api.utils.accounts.azure import get_azure_account_by_id


def update_azure_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.
    """
    user = get_user_by_username(job_doc['requesting_user'])
    cloud_account = get_azure_account_by_id(job_doc['cloud_account'], user.id)

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
        'emails',
        'label',
        'offer_id',
        'publisher_id',
        'sku'
    )
    sas_args = (
        job_doc.get('sas_token'),
        job_doc.get('sas_container'),
        job_doc.get('sas_storage_account')
    )

    if any(sas_args) and not all(sas_args):
        raise MashJobException(
            'sas_token, sas_storage_account and sas_container are all '
            'required for an Azure SAS upload job.'
        )

    if job_doc.get('sas_token'):
        if job_doc['last_service'] != 'uploader':
            raise MashJobException(
                'Azure uploads using SAS token expect a last service of uploader.'
            )
    else:
        for attr in attrs:
            if attr not in job_doc:
                job_doc[attr] = getattr(cloud_account, attr)

        if job_doc['last_service'] in ('publisher', 'deprecation'):
            for arg in publisher_args:
                if arg not in job_doc:
                    raise MashJobException(
                        'Azure publishing jobs require a(n) '
                        ' {arg} argument in the job document.'.format(
                            arg=arg
                        )
                    )

    return job_doc
