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
from mash.services.deprecation.azure_job import AzureDeprecationJob
from mash.services.deprecation.ec2_job import EC2DeprecationJob
from mash.services.deprecation.gce_job import GCEDeprecationJob
from mash.services.publisher.azure_job import AzurePublisherJob
from mash.services.publisher.ec2_job import EC2PublisherJob
from mash.services.publisher.gce_job import GCEPublisherJob
from mash.services.raw_image_uploader.s3bucket_job import S3BucketUploaderJob
from mash.services.replication.azure_job import AzureReplicationJob
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.gce_job import GCEReplicationJob
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob
from mash.services.uploader.azure_job import AzureUploaderJob
from mash.services.uploader.ec2_job import EC2UploaderJob
from mash.services.uploader.gce_job import GCEUploaderJob

jobs = {
    'deprecation': {
        'azure': AzureDeprecationJob,
        'ec2': EC2DeprecationJob,
        'gce': GCEDeprecationJob
    },
    'publisher': {
        'azure': AzurePublisherJob,
        'ec2': EC2PublisherJob,
        'gce': GCEPublisherJob
    },
    'raw_image_uploader': {
        's3bucket': S3BucketUploaderJob
    },
    'replication': {
        'azure': AzureReplicationJob,
        'ec2': EC2ReplicationJob,
        'gce': GCEReplicationJob
    },
    'testing': {
        'azure': AzureTestingJob,
        'ec2': EC2TestingJob,
        'gce': GCETestingJob
    },
    'uploader': {
        'azure': AzureUploaderJob,
        'ec2': EC2UploaderJob,
        'gce': GCEUploaderJob
    }
}


class JobFactory(object):
    """
    Service Job Factory class.
    """
    @staticmethod
    def create_job(
        cloud, service_exchange, job_config, service_config
    ):
        """
        Create new instance of job based on service exchange and cloud name,
        """
        try:
            if service_exchange == 'raw_image_uploader':
                # raw image uploader job type depends on a separate parameter
                # instead of the cloud framework
                job_class = jobs['raw_image_uploader'][job_config['raw_image_upload_type']]
            else:
                job_class = jobs[service_exchange][cloud]
        except KeyError:
            raise MashJobException(
                'Cloud {0} is not supported in {1} service.'.format(
                    cloud,
                    service_exchange
                )
            )

        try:
            job = job_class(job_config, service_config)
        except Exception as error:
            raise MashJobException(
                'Invalid job configuration: {0}'.format(error)
            )

        return job
