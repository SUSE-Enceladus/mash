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

from mash.mash_exceptions import MashConfigException
from mash.services.credentials.config import CredentialsConfig
from mash.services.deprecation.config import DeprecationConfig
from mash.services.jobcreator.config import JobCreatorConfig
from mash.services.logger.config import LoggerConfig
from mash.services.obs.config import OBSConfig
from mash.services.publisher.config import PublisherConfig
from mash.services.replication.config import ReplicationConfig
from mash.services.testing.config import TestingConfig
from mash.services.uploader.config import UploaderConfig

from mash.mash_exceptions import MashJobException
from mash.services.deprecation.azure_job import AzureDeprecationJob
from mash.services.deprecation.ec2_job import EC2DeprecationJob
from mash.services.deprecation.gce_job import GCEDeprecationJob
from mash.services.publisher.azure_job import AzurePublisherJob
from mash.services.publisher.ec2_job import EC2PublisherJob
from mash.services.publisher.gce_job import GCEPublisherJob
from mash.services.replication.azure_job import AzureReplicationJob
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.gce_job import GCEReplicationJob
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob

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
    'replication': {
        'azure': AzureReplicationJob,
        'ec2': EC2ReplicationJob,
        'gce': GCEReplicationJob
    },
    'testing': {
        'azure': AzureTestingJob,
        'ec2': EC2TestingJob,
        'gce': GCETestingJob
    }
}


def get_configuration(service, config_file=None):
    """
    MASH configuration factory.

    Return instance of config based on service name.
    """
    if service == 'credentials':
        return CredentialsConfig(config_file=config_file)
    elif service == 'deprecation':
        return DeprecationConfig(config_file=config_file)
    elif service == 'jobcreator':
        return JobCreatorConfig(config_file=config_file)
    elif service == 'logger':
        return LoggerConfig(config_file=config_file)
    elif service == 'obs':
        return OBSConfig(config_file=config_file)
    elif service == 'publisher':
        return PublisherConfig(config_file=config_file)
    elif service == 'replication':
        return ReplicationConfig(config_file=config_file)
    elif service == 'testing':
        return TestingConfig(config_file=config_file)
    elif service == 'uploader':
        return UploaderConfig(config_file=config_file)
    else:
        raise MashConfigException(
            'No configuration available for {0} service.'.format(service)
        )


class Job(object):
    """
    Service Job Factory.

    Attributes:

    * :attr:`cloud`
        cloud service provider name

    * :attr:`service_exchange`
        service exchange name

    * :attr:`job_config`
        job json configuration

    * :attr:`service_config`
        service configuration object
    """
    def __new__(
        self, cloud, service_exchange, job_config, service_config
    ):
        try:
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
