# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
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
from mash.services.upload.config import UploadConfig
from mash.services.listener_service import ListenerService
from mash.services.job_factory import BaseJobFactory

from mash.services.upload.azure_job import AzureUploadJob
from mash.services.upload.azure_raw_job import AzureRawUploadJob
from mash.services.upload.azure_sas_job import AzureSASUploadJob
from mash.services.upload.gce_job import GCEUploadJob
from mash.services.no_op_job import NoOpJob
from mash.services.upload.s3bucket_job import S3BucketUploadJob
from mash.services.upload.oci_job import OCIUploadJob


def main():
    """
    mash - upload service application entry point
    """
    try:
        logging.basicConfig()
        log = logging.getLogger('MashService')
        log.setLevel(logging.DEBUG)

        service_name = 'upload'

        # Create job factory
        job_factory = BaseJobFactory(
            service_name=service_name,
            job_types={
                'azure': AzureUploadJob,
                'azure_raw': AzureRawUploadJob,
                'azure_sas': AzureSASUploadJob,
                'ec2': NoOpJob,
                's3bucket': S3BucketUploadJob,
                'gce': GCEUploadJob,
                'oci': OCIUploadJob
            }
        )

        # run service, enter main loop
        ListenerService(
            service_exchange=service_name,
            config=UploadConfig(),
            custom_args={
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
