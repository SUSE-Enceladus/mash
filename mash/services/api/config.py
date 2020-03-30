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

from mash.services.base_config import BaseConfig


class Config(object):
    """
    Flask API config.
    """

    def __init__(self, config_file=None, testing=False):
        self.config = BaseConfig(config_file)
        self.TESTING = testing

    @property
    def AMQP_HOST(self):
        return self.config.get_amqp_host()

    @property
    def AMQP_USER(self):
        return self.config.get_amqp_user()

    @property
    def AMQP_PASS(self):
        return self.config.get_amqp_pass()

    @property
    def LOG_FILE(self):
        return self.config.get_log_file('api')

    @property
    def CREDENTIALS_URL(self):
        return self.config.get_credentials_url()

    @property
    def CLOUD_DATA(self):
        return self.config.get_cloud_data()

    @property
    def JWT_BLACKLIST_ENABLED(self):
        return True

    @property
    def JWT_SECRET_KEY(self):
        return self.config.get_jwt_secret()

    @property
    def SQLALCHEMY_TRACK_MODIFICATIONS(self):
        return False

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self.config.get_database_uri()

    @property
    def EMAIL_WHITELIST(self):
        return self.config.get_email_whitelist()

    @property
    def DOMAIN_WHITELIST(self):
        return self.config.get_domain_whitelist()

    @property
    def AUTH_METHODS(self):
        return self.config.get_auth_methods()

    @property
    def OAUTH2_CLIENT_ID(self):
        return self.config.get_oauth2_client_id()

    @property
    def OAUTH2_CLIENT_SECRET(self):
        return self.config.get_oauth2_client_secret()

    @property
    def OAUTH2_PROVIDER_URL(self):
        return self.config.get_oauth2_provider_url()

    @property
    def OAUTH2_REDIRECT_PORTS(self):
        return self.config.get_oauth2_redirect_ports()

    @property
    def SMTP_HOST(self):
        return self.config.get_smtp_host()

    @property
    def SMTP_PORT(self):
        return self.config.get_smtp_port()

    @property
    def SMTP_USER(self):
        return self.config.get_smtp_user()

    @property
    def SMTP_PASS(self):
        return self.config.get_smtp_pass()

    @property
    def SMTP_SSL(self):
        return self.config.get_smtp_ssl()
