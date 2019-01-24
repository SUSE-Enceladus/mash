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


class UploadBase(object):
    """
    Implements base upload interface class

    Attributes

    * :attr:`credentials`
        cloud access information

    * :attr:`system_image_file`
        path to the compressed system image to upload

    * :attr:`cloud_image_name`
        name of the image in the public cloud
        has to follow naming conventions from here: ...

    * :attr:`cloud_image_description`
        description of the image in the public cloud

    * :attr:`custom_args`
        dictionary including cloud provider specific
        arguments required for uploading.

    * :attr:`arch`
        image architecture, defaults to: x86_64
    """
    def __init__(
        self, credentials, system_image_file, cloud_image_name,
        cloud_image_description, custom_args, arch='x86_64'
    ):
        self.arch = arch
        self.system_image_file = system_image_file
        self.cloud_image_name = cloud_image_name
        self.cloud_image_description = cloud_image_description
        self.credentials = credentials
        self.custom_args = custom_args

        self.post_init()

    def post_init(self):
        pass

    def upload(self):
        raise NotImplementedError
