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
from mash.services.uploader.cloud.amazon import UploadAmazon
from mash.services.uploader.cloud.azure import UploadAzure
from mash.services.uploader.conventions import Conventions
from mash.csp import CSP

from mash.mash_exceptions import MashUploadSetupException


class Upload(object):
    """
    System Image Upload Factory

    Attributes

    * :attr:`csp_name`
        cloud service provider name

    * :attr:`system_image_file`
        path to the system image to upload

    * :attr:`cloud_image_name`
        name of the image in the public cloud

    * :attr:`cloud_image_description`
        description of the image in the public cloud

    * :attr:`credentials`
        cloud access information

    * :attr:`custom_uploader_args`
        custom argument hash for uploader, cloud specific
    """
    def __new__(
        self, csp_name, system_image_file,
        cloud_image_name, cloud_image_description, credentials,
        custom_uploader_args=None
    ):
        conventions = Conventions(csp_name)
        conventions.is_valid_name(cloud_image_name)

        if csp_name == CSP.ec2:
            return UploadAmazon(
                credentials, system_image_file, cloud_image_name,
                cloud_image_description, custom_uploader_args
            )
        elif csp_name == CSP.azure:
            return UploadAzure(
                credentials, system_image_file, cloud_image_name,
                cloud_image_description, custom_uploader_args
            )
        else:
            raise MashUploadSetupException(
                'Support for {csp} Cloud Service not implemented'.format(
                    csp=csp_name
                )
            )
