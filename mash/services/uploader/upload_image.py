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

# project
from mash.services.uploader.cloud import Upload


class UploadImage(object):
    """
    Process an upload into the public cloud

    * :attr:`job_id`
        job number

    * :attr:`job_file`
        job file containing the job description

    * :attr:`csp_name`
        cloud service provider name

    * :attr:`credentials_token`
        credentials token for target cloud system

    * :attr:`cloud_image_name`
        name of the image in the public cloud
        has to follow naming conventions

    * :attr:`cloud_image_description`
        description of the image in the public cloud

    * :attr:`custom_uploader_args`
        dictionary of parameters for the used upload tool
        specific to the selected cloud and uploader class

    * :attr:`arch`
        image architecture, defaults to: x86_64
    """
    def __init__(
        self, job_id, job_file, csp_name, credentials_token,
        cloud_image_name, cloud_image_description, region,
        custom_uploader_args=None, arch='x86_64'
    ):
        self.job_id = job_id
        self.job_file = job_file
        self.arch = arch
        self.csp_name = csp_name

        self.cloud_image_name = cloud_image_name
        self.cloud_image_description = cloud_image_description
        self.custom_uploader_args = custom_uploader_args

        self.credentials_token = credentials_token

        self.system_image_file = None
        self.result_callback = None
        self.log_callback = None
        self.cloud_image_id = None
        self.upload_region = region
        self.iteration_count = 0
        self.uploader = None
        self.error_msg = None

    def set_image_file(self, system_image_file):
        self.system_image_file = system_image_file

    def upload(self):
        """
        Upload image to the specified cloud

        Creates an instance of the Upload factory and returns
        an image identifier once the upload has been processed
        successfully. The image identifier is cloud specific
        as well as the information handed over in the custom
        uploader and credentials arguments
        """
        if self.system_image_file:
            self.iteration_count += 1
            self._log_callback(
                'Uploading image to {0}: {1}:{2}'.format(
                    self.csp_name, self.system_image_file,
                    self.custom_uploader_args
                )
            )
            try:
                self.uploader = Upload(
                    self.csp_name, self.system_image_file,
                    self.cloud_image_name, self.cloud_image_description,
                    self.credentials_token,
                    self.custom_uploader_args,
                    self.arch
                )
                self.cloud_image_id = self.uploader.upload()
                self._log_callback(
                    'Uploaded image has ID: {0} in region {1}'.format(
                        self.cloud_image_id, self.upload_region)
                )
            except Exception as e:
                self._log_callback(format(e))
                self.error_msg = e

            self._result_callback()

    def set_log_handler(self, function):
        self.log_callback = function

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def _result_callback(self):
        if self.result_callback:
            if self.cloud_image_id:
                job_status = 'success'
            else:
                job_status = 'failed'
            self.result_callback(
                self.job_id, {
                    'csp_name': self.csp_name,
                    'cloud_image_id': self.cloud_image_id,
                    'upload_region': self.upload_region,
                    'job_status': job_status,
                    'error_msg': self.error_msg
                }
            )

    def _log_callback(self, message):
        if self.log_callback:
            self.log_callback(
                self.job_id, 'Pass[{0}]: {1}'.format(
                    self.iteration_count, message
                )
            )
