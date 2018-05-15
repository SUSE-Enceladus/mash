# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

from jsonschema import FormatChecker, validate

from mash.csp import CSP
from mash.mash_exceptions import (
    MashJobCreatorException,
    MashValidationException
)
from mash.services.jobcreator import schema
from mash.services.jobcreator.ec2_job import EC2Job


def create_job(job_doc, accounts_info):
    csp_name = job_doc.get('provider')
    accounts_info = accounts_info.get(csp_name)

    if csp_name == CSP.ec2:
        job_class = EC2Job
        message_schema = schema.ec2_job_message
    else:
        raise MashJobCreatorException(
            'Support for {csp} Cloud Service not implemented'.format(
                csp=csp_name
            )
        )

    try:
        validate(job_doc, message_schema, format_checker=FormatChecker())
    except Exception as error:
        raise MashValidationException(error)
    else:
        return job_class(accounts_info, **job_doc)
