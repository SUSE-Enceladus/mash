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
import os
import pickle
from apscheduler.schedulers.background import BackgroundScheduler

from amqpstorm import Connection

# project
from mash.utils.json_format import JsonFormat
from mash.services.uploader.cloud import Upload
from mash.services.uploader.defaults import Defaults
from mash.mash_exceptions import (
    MashJobRetireException
)


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

    * :attr:`job_file`
        job file containing the job description

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
        self, job_id, job_file, csp_name,
        cloud_image_name, cloud_image_description,
        host='localhost', service_lookup_timeout_sec=None,
        custom_uploader_args=None, custom_credentials_args=None
    ):
        self.job_id = job_id
        self.job_file = job_file
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
        self.image_file_uploaded = None
        self.credentials_token = None
        self.consuming_timeout_reached = False
        self.result_callback = None
        self.log_callback = None
        self.cloud_image_id = None
        self.connection = None
        self.channel = None
        self.iteration_count = 0
        self.uploader = None

        self.scheduler = BackgroundScheduler()
        self.job = self.scheduler.add_job(
            self._consume_service_information
        )
        self.scheduler.start()

    def upload(self, oneshot=True):
        """
        Upload image to the specified cloud

        Creates an instance of the Upload factory and returns
        an image identifier once the upload has been processed
        successfully. The image identifier is cloud specific
        as well as the information handed over in the custom
        uploader and credentials arguments

        :param bool oneshot: pickle object instance after upload
        """
        while True:
            # wait for background thread to provide required information
            self.iteration_count += 1
            self._log_callback(
                'Waiting for image and credentials data'
            )
            # send obs service listen request
            self._set_listen_request_for_obs_image()
            while True:
                if self.consuming_timeout_reached:
                    self._log_callback(
                        'Waiting for image and credentials timed out'
                    )
                    return
                if self.system_image_file and self.credentials_token:
                    break
                else:
                    time.sleep(1)

            # upload to the cloud. For nonstop uploads the upload is
            # repeated after a delay and only if the image file has
            # changed but with the same credentials as before
            delay_time_sec = 30
            if self.image_file_uploaded != self.system_image_file:
                self._log_callback(
                    'Uploading image to {0}: {1}'.format(
                        self.csp_name, self.system_image_file
                    )
                )
                self.uploader = Upload(
                    self.csp_name, self.system_image_file,
                    self.cloud_image_name, self.cloud_image_description,
                    self.credentials_token,
                    self.custom_uploader_args,
                    self.custom_credentials_args
                )
                try:
                    self.cloud_image_id = self.uploader.upload()
                    self.image_file_uploaded = self.system_image_file
                    self._log_callback(
                        'Uploaded image has ID: {0}'.format(self.cloud_image_id)
                    )
                except Exception as e:
                    self._log_callback(format(e))

                if oneshot:
                    self._retire()

            # report current result
            if self.image_file_uploaded:
                self._result_callback()

            if not oneshot:
                self._log_callback(
                    'Waiting {0}sec before next try...'.format(delay_time_sec)
                )
                # reset previous image file name
                self.system_image_file = None
                time.sleep(delay_time_sec)
            else:
                self._close_connection()
                break

        return self.cloud_image_id

    def set_log_handler(self, function):
        self.log_callback = function

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def stop(self):
        self._log_callback(
            'Deleting active uploader via timeout interrupt'
        )
        self._consuming_timeout()
        if self.uploader:
            del self.uploader

    def _retire(self):
        try:
            # temporary delete what we can't pickle from self.__dict__
            job_backup = self.job
            scheduler_backup = self.scheduler
            log_callback_backup = self.log_callback
            result_callback_backup = self.result_callback
            connection_backup = self.connection
            channel_backup = self.channel
            retired_job = os.sep.join(
                [Defaults.get_jobs_done_dir(), self.job_id + '.pickle']
            )
            os.remove(self.job_file)
            self.job_file = retired_job
            with open(retired_job, 'wb') as retired:
                self.job = None
                self.scheduler = None
                self.log_callback = None
                self.result_callback = None
                self.connection = None
                self.channel = None
                pickle.dump(self, retired)
            self.log_callback = log_callback_backup
            self.result_callback = result_callback_backup
            self.job = job_backup
            self.scheduler = scheduler_backup
            self.connection = connection_backup
            self.channel = channel_backup
        except Exception as e:
            raise MashJobRetireException(
                'Retire Job failed with: {0}'.format(e)
            )

    def _result_callback(self):
        if self.result_callback and self.cloud_image_id:
            self.result_callback(
                self.job_id, {
                    'csp_name': self.csp_name,
                    'cloud_image_id': self.cloud_image_id
                }
            )

    def _log_callback(self, message):
        if self.log_callback:
            self.log_callback(
                self.job_id, 'Pass[{0}]: {1}'.format(
                    self.iteration_count, message
                )
            )

    def _set_listen_request_for_obs_image(self):
        exchange = 'obs'
        routing_key = 'service_event'
        body = '{{"obsjob_listen": "{0}"}}'.format(self.job_id)
        self._log_callback(
            'Sending listen request for obs image'
        )
        connection = Connection(
            self.host, 'guest', 'guest', kwargs={'heartbeat': 600}
        )
        channel = connection.channel()
        channel.queue.declare(
            queue='{0}.{1}'.format(exchange, routing_key), durable=True
        )
        channel.basic.publish(
            body, routing_key, exchange, mandatory=True,
        )
        channel.close()
        connection.close()

    def _consume_service_information(self):
        self.connection = Connection(
            self.host, 'guest', 'guest', kwargs={'heartbeat': 600}
        )
        self.channel = self.connection.channel()
        # lookup authenitcation data from credentials service
        self.channel.queue.declare(
            queue=self.credentials_listen_queue, durable=True
        )
        self.channel.basic.consume(
            callback=self._service_data, queue=self.credentials_listen_queue
        )
        # lookup image file data from obs service
        self.channel.queue.declare(
            queue=self.obs_listen_queue, durable=True
        )
        self.channel.basic.consume(
            callback=self._service_data, queue=self.obs_listen_queue
        )
        try:
            if self.service_lookup_timeout_sec:
                self._timed_consume(self.service_lookup_timeout_sec)
            else:
                self.channel.start_consuming()
        except Exception:
            self._close_connection()

    def _timed_consume(self, timeout):
        end = time.time() + timeout
        while self.channel.is_open and time.time() < end:
            self.channel.process_data_events()
            if not self.channel.consumer_tags:
                break

        if self.channel.consumer_tags:
            self._consuming_timeout()

    def _service_data(self, message):
        message.ack()
        service_data = JsonFormat.json_loads(message.body)
        if 'image_source' in service_data:
            self.system_image_file = service_data['image_source'][0]
            self._log_callback(
                'Got image file: {0}'.format(self.system_image_file)
            )
        if 'credentials' in service_data:
            self.credentials_token = service_data['credentials']
            self._log_callback(
                'Got credentials data'
            )

    def _consuming_timeout(self):
        self.consuming_timeout_reached = True
        self._close_connection()

    def _close_connection(self):
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
