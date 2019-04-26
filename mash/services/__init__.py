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
