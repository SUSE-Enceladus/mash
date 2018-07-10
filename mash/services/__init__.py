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


def get_configuration(service):
    """
    MASH configuration factory.

    Return instance of config based on service name.
    """
    if service == 'credentials':
        return CredentialsConfig()
    elif service == 'deprecation':
        return DeprecationConfig()
    elif service == 'jobcreator':
        return JobCreatorConfig()
    elif service == 'logger':
        return LoggerConfig()
    elif service == 'obs':
        return OBSConfig()
    elif service == 'publisher':
        return PublisherConfig()
    elif service == 'replication':
        return ReplicationConfig()
    elif service == 'testing':
        return TestingConfig()
    elif service == 'uploader':
        return UploaderConfig()
    else:
        raise MashConfigException(
            'No configuration available for {0} service.'.format(service)
        )
