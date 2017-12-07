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
import time
from apscheduler.schedulers.background import BackgroundScheduler

from amqpstorm import UriConnection

# project
from mash.utils.json_format import JsonFormat
from mash.services.uploader.cloud import Upload


class UploadImage(object):
    """
    Process an upload into the public cloud

    Before an upload can start information from the obs service
    about the image and information about the credentials from the
    credentials service to access the cloud needs to be retrieved.
    This class implements the pipeline connection to obs and credentials
    services and provides an interface to upload into the cloud

    * :attr:`job_id`
        job number

    * :attr:`csp_name`
        cloud service provider name

    * :attr:`cloud_image_name`
        name of the image in the public cloud
        has to follow naming conventions

    * :attr:`cloud_image_description`
        description of the image in the public cloud

    * :attr:`host`
        rabbit connection host, defaults to localhost

    * :attr:`service_lookup_timeout_sec`
        optional timeout for waiting on results of services

    * :attr:`custom_uploader_args`
        dictionary of parameters for the used upload tool
        specific to the selected cloud and uploader class

    * :attr:`custom_credentials_args`
        dictionary of parameters for the instance handling
        credentials. specific to the selected cloud and
        credentials class
    """
    def __init__(
        self, job_id, csp_name, cloud_image_name, cloud_image_description,
        host='localhost', service_lookup_timeout_sec=None,
        custom_uploader_args=None, custom_credentials_args=None
    ):
        self.job_id = job_id
        self.csp_name = csp_name
        self.host = host
        self.cloud_image_name = cloud_image_name
        self.cloud_image_description = cloud_image_description
        self.custom_uploader_args = custom_uploader_args
        self.custom_credentials_args = custom_credentials_args
        self.service_lookup_timeout_sec = service_lookup_timeout_sec

        self.obs_listen_queue = 'obs.listener_{0}'.format(
            self.job_id
        )
        self.credentials_listen_queue = 'credentials.{0}_{1}'.format(
            self.csp_name, self.job_id
        )

        self.system_image_file = None
        self.credentials_token = None
        self.consuming_timeout_reached = False
        self.connection = None
        self.channel = None

        self.scheduler = BackgroundScheduler()
        self.job = self.scheduler.add_job(
            self._consume_service_information
        )
        self.scheduler.start()

    def upload(self):
        """
        Upload image to the specified cloud

        Creates an instance of the Upload factory and returns
        an image identifier once the upload has been processed
        successfully. The image identifier is cloud specific
        as well as the information handed over in the custom
        uploader and credentials arguments
        """
        # wait for background thread to provide required information
        while True:
            if self.consuming_timeout_reached:
                return
            if self.system_image_file and self.credentials_token:
                break
            else:
                time.sleep(1)

        # upload to the cloud
        uploader = Upload(
            self.csp_name, self.system_image_file,
            self.cloud_image_name, self.cloud_image_description,
            self.credentials_token,
            self.custom_uploader_args,
            self.custom_credentials_args
        )
        return uploader.upload()

    def _consume_service_information(self):
        self.connection = UriConnection(
            'amqp://guest:guest@{0}:5672/%2F?heartbeat=600'.format(
                self.host
            )
        )
        self.channel = self.connection.channel()
        # lookup authenitcation data from credentials service
        self.channel.queue.declare(
            queue=self.credentials_listen_queue, durable=True
        )
        self.channel.basic.consume(
            callback=self._credentials_job_data,
            queue=self.credentials_listen_queue
        )
        # lookup image file data from obs service
        self.channel.queue.declare(
            queue=self.obs_listen_queue, durable=True
        )
        self.channel.basic.consume(
            callback=self._obs_job_data, queue=self.obs_listen_queue
        )
        try:
            if self.service_lookup_timeout_sec:
                self._timed_consume(self.service_lookup_timeout_sec)
            else:
                self.channel.start_consuming(to_tuple=True)
        except Exception:
            self._close_connection()

    def _timed_consume(self, timeout=None):
        end = time.time() + timeout
        while self.channel.is_open and time.time() < end:
            self.channel.process_data_events()
            if not self.channel.consumer_tags:
                break

        if self.channel.consumer_tags:
            self._consuming_timeout()

    def _obs_job_data(self, body, channel, method, properties):
        channel.basic.ack(delivery_tag=method['delivery_tag'])
        channel.queue.delete(queue=self.obs_listen_queue)
        obs_result = JsonFormat.json_loads_byteified(body)
        self.system_image_file = obs_result['image_source'][0]

    def _credentials_job_data(self, body, channel, method, properties):
        channel.basic.ack(delivery_tag=method['delivery_tag'])
        channel.queue.delete(queue=self.credentials_listen_queue)
        credentials_result = JsonFormat.json_loads_byteified(body)
        self.credentials_token = credentials_result['credentials']

    def _consuming_timeout(self):
        self.consuming_timeout_reached = True
        self._close_connection()

    def _close_connection(self):
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
