# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

from mash.csp import CSP
from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.azure_job import AzureJob
from mash.services.jobcreator.ec2_job import EC2Job
from mash.services.jobcreator.gce_job import GCEJob


def create_job(job_doc, accounts_info, cloud_data):
    csp_name = job_doc.get('cloud')
    cloud_data = cloud_data.get(csp_name)

    if csp_name == CSP.ec2:
        job_class = EC2Job
    elif csp_name == CSP.azure:
        job_class = AzureJob
    elif csp_name == CSP.gce:
        job_class = GCEJob
    else:
        raise MashJobCreatorException(
            'Support for {csp} Cloud Service not implemented'.format(
                csp=csp_name
            )
        )

    return job_class(accounts_info, cloud_data, **job_doc)
