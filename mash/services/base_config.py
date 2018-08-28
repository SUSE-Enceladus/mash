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
import yaml

from mash.mash_exceptions import MashConfigException
from mash.services.base_defaults import Defaults


class BaseConfig(object):
    """
    Implements reading of a yaml configuration file:

    The mash configuration files are yaml formatted files containing
    information to control the behavior of each service.
    """
    def __init__(self, config_file=None):
        config_file = config_file or Defaults.get_config()
        self.config_data = None
        try:
            with open(config_file, 'r') as config:
                self.config_data = yaml.load(config)
        except Exception as e:
            raise MashConfigException(
                'Failed reading config file: {config}: {error}'.format(
                    config=config_file, error=e
                )
            )

    def _get_attribute(self, attribute, element=None):
        if self.config_data:
            if element:
                if self.config_data.get(element):
                    return self.config_data[element].get(attribute)
            else:
                return self.config_data.get(attribute)

    def get_encryption_keys_file(self):
        """
        Return the encryption keys file path.

        :rtype: string
        """
        encryption_keys_file = self._get_attribute(
            attribute='encryption_keys_file'
        )
        return encryption_keys_file or Defaults.get_encryption_keys_file()

    def get_jwt_algorithm(self):
        """
        Return JWT algorithm from MASH config file.

        algorithm is used for decoding JWT tokens.
        """
        algorithm = self._get_attribute(attribute='jwt_algorithm')
        return algorithm or Defaults.get_jwt_algorithm()

    def get_jwt_secret(self):
        """
        Return JWT secret token from MASH config file.

        Raise exception if secret not in config file.
        """
        secret = self._get_attribute(attribute='jwt_secret')

        if not secret:
            raise MashConfigException('jwt_secret must be in config file.')

        return secret

    def get_log_directory(self):
        """
        Return log directory path based on log_dir attribute.

        :rtype: string
        """
        log_dir = self._get_attribute(attribute='log_dir')
        return log_dir or Defaults.get_log_directory()

    def get_log_file(self, service):
        """
        Return log file name based on log_dir attribute.

        :rtype: string
        """
        log_dir = self.get_log_directory()
        return '{dir}{service}_service.log'.format(
            dir=log_dir, service=service
        )

    def get_provider_data(self):
        """
        Return the provider data from config.
        """
        data = self._get_attribute(attribute='provider')

        if not data:
            raise MashConfigException(
                'Provider data must be provided in config file.'
            )

        return data

    def get_service_names(self, credentials_required=False):
        """
        Return a list of all service names.

        If credentials_required is True return only services that require
        credentials to execute.
        """
        services = self._get_attribute(attribute='services') or \
            Defaults.get_service_names()

        if credentials_required:
            non_cred_services = self._get_attribute(
                attribute='non_cred_services'
            ) or Defaults.get_non_credential_service_names()
            services = [service for service in services
                        if service not in non_cred_services]

        return services

    def get_ssh_private_key_file(self):
        """
        Return the path to the ssh private key file.

        :rtype: string
        """
        private_key_file = self._get_attribute(
            attribute='ssh_private_key_file'
        )

        if not private_key_file:
            raise MashConfigException(
                'ssh_private_key_file is required in MASH configuration file.'
            )

        return private_key_file

    def get_amqp_host(self):
        """
        Return the amqp host url.

        :rtype: string
        """
        amqp_host = self._get_attribute(
            attribute='amqp_host'
        )

        return amqp_host or Defaults.get_amqp_host()

    def get_amqp_user(self):
        """
        Return the amqp user name.

        :rtype: string
        """
        amqp_user = self._get_attribute(
            attribute='amqp_user'
        )

        return amqp_user or Defaults.get_amqp_user()

    def get_amqp_pass(self):
        """
        Return the amqp password.

        :rtype: string
        """
        amqp_pass = self._get_attribute(
            attribute='amqp_pass'
        )

        return amqp_pass or Defaults.get_amqp_pass()
