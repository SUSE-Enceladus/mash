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
import logging
import sys
import traceback

# project
from mash.mash_exceptions import MashException
from mash.services.base_config import BaseConfig
from mash.services.listener_service import ListenerService
from mash.services.job_factory import BaseJobFactory

from mash.services.create.azure_job import AzureCreateJob
from mash.services.create.ec2_job import EC2CreateJob
from mash.services.create.gce_job import GCECreateJob


def main():
    """
    mash - create service application entry point
    """
    try:
        logging.basicConfig()
        log = logging.getLogger('MashService')
        log.setLevel(logging.DEBUG)

        service_name = 'create'

        # Create job factory
        job_factory = BaseJobFactory(
            service_name=service_name,
            job_types={
                'azure': AzureCreateJob,
                'ec2': EC2CreateJob,
                'gce': GCECreateJob
            }
        )

        # run service, enter main loop
        ListenerService(
            service_exchange=service_name,
            config=BaseConfig(),
            custom_args={
                'listener_msg_args': ['image_file', 'source_regions'],
                'status_msg_args': ['image_file', 'source_regions'],
                'job_factory': job_factory
            }
        )
    except MashException as e:
        # known exception
        log.error('{0}: {1}'.format(type(e).__name__, format(e)))
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except SystemExit:
        # user exception, program aborted by user
        sys.exit(0)
    except Exception as e:
        # exception we did no expect, show python backtrace
        log.error('Unexpected error: {0}'.format(e))
        traceback.print_exc()
        sys.exit(1)
