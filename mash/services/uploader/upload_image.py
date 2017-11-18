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
import pika

# project
from mash.utils.json_format import JsonFormat
from mash.services.uploader.cloud import Upload


class UploadImage(object):
    """
    Base class to process an upload into the public cloud

    Before an upload can start information from the obs service
    about the image and information about the credentials to
    access the cloud needs to be retrieved. This class implements
    the pipeline connection to obs and credentials services
    and provides an interface to upload into the cloud
    """
    def __init__(
        self, job_id, csp_name,
        cloud_image_name, cloud_image_description, credentials_token,
        custom_uploader_args=None, custom_credentials_args=None,
        host='localhost'
    ):
        self.job_id = job_id
        self.csp_name = csp_name
        self.cloud_image_name = cloud_image_name
        self.cloud_image_description = cloud_image_description
        self.host = host
        self.obs_listen_queue = 'obs.listener_{0}'.format(
            self.job_id
        )
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host)
        )
        self.channel = self.connection.channel()
        self.custom_uploader_args = custom_uploader_args
        self.custom_credentials_args = custom_credentials_args
        self.credentials_token = credentials_token
        self.system_image_file = None

    def upload(self, obs_lookup_timeout=None):
        uploader = Upload(
            self.csp_name, self._get_obs_image(obs_lookup_timeout),
            self.cloud_image_name, self.cloud_image_description,
            self.credentials_token,
            self.custom_uploader_args,
            self.custom_credentials_args
        )
        return uploader.upload()

    def _get_obs_image(self, timeout=None):
        """
        Provide image from the obs service for the specified job

        At best this information is present at the time we want
        to upload. If no timeout is specified this call will
        block the upload until the obs service provided some
        information.
        """
        self.channel.queue_declare(
            queue=self.obs_listen_queue, durable=True
        )
        self.channel.basic_consume(
            self._obs_job_data, queue=self.obs_listen_queue
        )
        if timeout:
            self.connection.add_timeout(
                timeout, self._obs_job_timeout
            )
        self.channel.start_consuming()
        return self.system_image_file

    def _obs_job_data(self, channel, method, properties, body):
        self._obs_delete_queue()
        obs_result = JsonFormat.json_loads_byteified(body)
        self.system_image_file = obs_result['image_source'][0]

    def _obs_job_timeout(self):
        self._obs_delete_queue()

    def _obs_delete_queue(self):
        self.channel.queue_delete(queue=self.obs_listen_queue)
