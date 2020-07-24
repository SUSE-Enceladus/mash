# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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
    def __init__(self, config_file=None, test=False):
        self.config = BaseConfig(config_file)
        self.service_exchange = 'database'
        self.TESTING = test

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
        return self.config.get_log_file(self.service_exchange)

    @property
    def SQLALCHEMY_TRACK_MODIFICATIONS(self):
        return False

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self.config.get_database_uri()

    @property
    def CREDENTIALS_URL(self):
        return self.config.get_credentials_url()
