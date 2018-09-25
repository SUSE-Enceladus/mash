# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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
import os

from tempfile import NamedTemporaryFile

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.storage.drivers.google_storage import GoogleStorageDriver

# project
from mash.services import get_configuration
from mash.services.uploader.cloud.base import UploadBase
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat


class UploadGCE(UploadBase):
    """
    Implements system image upload to GCE

    GCE specific custom arguments:

    .. code:: python

        custom_args={
            'bucket': 'images'
            'region': 'region_name'
        }
    """
    def post_init(self):
        if 'sles-11' in self.cloud_image_name:
            raise MashUploadException(
                'No SLES 11 support in mash for GCE.'
            )

        if not self.custom_args:
            self.custom_args = {}

        self.bucket = self.custom_args.get('bucket')
        if not self.bucket:
            raise MashUploadException(
                'required GCE bucket name for upload not specified'
            )

        self.region = self.custom_args.get('region')
        if not self.region:
            raise MashUploadException(
                'required GCE region name for upload not specified'
            )

        self._create_auth_file()

        self.config = get_configuration(service='uploader')

    def upload(self):
        storage_driver = GoogleStorageDriver(
            self.credentials['client_email'],
            secret=self.auth_file.name,
            project=self.credentials['project_id']
        )

        object_name = os.path.basename(self.system_image_file)
        container = storage_driver.get_container(self.bucket)
        with open(self.system_image_file, 'rb') as image_stream:
            storage_driver.upload_object_via_stream(
                image_stream, container, object_name
            )

        ComputeEngine = get_driver(Provider.GCE)
        compute_driver = ComputeEngine(
            self.credentials['client_email'],
            self.auth_file.name,
            project=self.credentials['project_id']
        )

        uri = ''.join([
            'https://www.googleapis.com/storage/v1/b/',
            self.bucket, '/o/', object_name
        ])
        name_components = self.cloud_image_name.split('-')
        family = '-'.join([name_components[0], name_components[1]])
        compute_driver.ex_create_image(
            self.cloud_image_name, uri,
            description=self.cloud_image_description,
            family=family
        )
        return self.cloud_image_name, self.region

    def _create_auth_file(self):
        self.auth_file = NamedTemporaryFile()
        with open(self.auth_file.name, 'w') as gce_auth:
            gce_auth.write(JsonFormat.json_message(self.credentials))
