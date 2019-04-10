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
    account_info = {}
    cloud = message['cloud']

    cloud_data = {
        CSP.ec2: ('additional_regions', 'partition', 'region'),
        CSP.azure: (
            'region', 'source_container', 'source_resource_group',
            'source_storage_account', 'destination_container',
            'destination_resource_group', 'destination_storage_account'
        ),
        CSP.gce: ('bucket', 'region', 'testing_account')
    }

    try:
        account_data = cloud_data[cloud]
    except KeyError:
        raise MashCredentialsException(
            'CSP {0} is not supported.'.format(cloud)
        )

    for key in account_data:
        account_info[key] = message.get(key)

    return account_info
