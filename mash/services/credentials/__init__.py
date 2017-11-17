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
# project
from mash.services.credentials.amazon import CredentialsAmazon
from mash.csp import CSP

from mash.mash_exceptions import MashCredentialsException


class Credentials(object):
    """
    Credentials Factory

    Attributes

    * :attr:`csp_name`
        cloud service provider name
    """
    def __new__(self, csp_name, custom_args=None):
        if csp_name == CSP.ec2:
            return CredentialsAmazon(custom_args)
        else:
            raise MashCredentialsException(
                'Support for {csp} Cloud Service not implemented'.format(
                    csp=csp_name
                )
            )
