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

from mash.csp import CSP

from mash.mash_exceptions import MashCredentialsException


def get_account_info(message):
    """
    Create a dictionary with account info based on cloud framework.
    """
    cloud = message['cloud']

    if cloud == CSP.ec2:
        account_info = {
            'additional_regions': message.get('additional_regions'),
            'partition': message['partition'],
            'region': message.get('region')
        }
    elif cloud == CSP.azure:
        account_info = {
            'region': message['region'],
            'source_container': message['source_container'],
            'source_resource_group': message['source_resource_group'],
            'source_storage_account': message['source_storage_account'],
            'destination_container': message['destination_container'],
            'destination_resource_group': message['destination_resource_group'],
            'destination_storage_account': message['destination_storage_account']
        }
    elif cloud == CSP.gce:
        account_info = {
            'bucket': message['bucket'],
            'region': message['region'],
            'testing_account': message.get('testing_account')
        }
    else:
        raise MashCredentialsException(
            'CSP {0} is not supported.'.format(cloud)
        )

    return account_info
