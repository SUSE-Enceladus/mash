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


class Defaults(object):
    """
    Default values
    """

    @classmethod
    def get_config(self):
        return '/etc/mash/mash_config.yaml'

    @classmethod
    def get_job_directory(self, service_name):
        return '/var/lib/mash/{0}_jobs/'.format(service_name)

    @classmethod
    def get_jwt_algorithm(self):
        return 'HS256'

    @classmethod
    def get_log_directory(self):
        return '/var/log/mash/'

    @classmethod
    def get_private_key_file(self):
        return '/etc/mash/creds_key'

    @classmethod
    def get_service_names(self):
        return [
            'obs', 'uploader', 'testing', 'replication', 'publisher',
            'deprecation', 'pint'
        ]

    @classmethod
    def get_non_credential_service_names(self):
        return ['obs']
