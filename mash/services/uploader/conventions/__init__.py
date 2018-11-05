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
from mash.services.uploader.conventions.amazon import ConventionsAmazon
from mash.services.uploader.conventions.azure import ConventionsAzure
from mash.services.uploader.conventions.gce import ConventionsGCE
from mash.csp import CSP

from mash.mash_exceptions import MashConventionsException


class Conventions(object):
    """
    Conventions Factory

    Attributes

    * :attr:`csp`
        cloud service provider name
    """
    def __new__(self, csp_name):
        if csp_name == CSP.ec2:
            return ConventionsAmazon()
        elif csp_name == CSP.azure:
            return ConventionsAzure()
        elif csp_name == CSP.gce:
            return ConventionsGCE()
        else:
            raise MashConventionsException(
                'Support for {csp} Cloud Service not implemented'.format(
                    csp=csp_name
                )
            )
