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

import json

from mash.services.mash_service import MashService
from mash.services.jobcreator import create_job
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import setup_logfile


class JobCreatorService(MashService):
    """
    Implementation of job creator service.

    Handles the orchestration of jobs for mash.
    """

    def post_init(self):
        """
        Initialize job creator service class.
        """
        self.service_queue = 'service'
        self.job_document_key = 'job_document'

        logfile_handler = setup_logfile(
            self.config.get_log_file(self.service_exchange)
        )
        self.log.addHandler(logfile_handler)
        self.services = self.config.get_service_names()

        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )

        self.start()

    def _handle_service_message(self, message):
        """
        Handle new and delete job messages.
        """
        try:
            job_doc = json.loads(message.body)
            if 'job_delete' in job_doc:
                self.publish_delete_job_message(job_doc['job_delete'])
            else:
                self.send_job(job_doc)
        except Exception as error:
            self.log.error(
                'Invalid message received: {0}.'.format(error)
            )

        message.ack()

    def publish_delete_job_message(self, job_id):
        """
        Publish delete job message to obs service.

        This will flush the job with the given id out of the pipeline.
        """
        self.log.info(
            'Deleting job.',
            extra={'job_id': job_id}
        )

        delete_message = {
            "obs_job_delete": job_id
        }
        self._publish(
            'obs', self.job_document_key, JsonFormat.json_message(delete_message)
        )

    def publish_job_doc(self, service, job_doc):
        """
        Publish the job_doc message to the given service exchange.
        """
        self._publish(service, self.job_document_key, job_doc)

    def send_job(self, job_doc):
        """
        Create instance of job and send to all services to initiate job.
        """
        job = create_job(job_doc)

        self.log.info(
            'Started a new job: {0}'.format(JsonFormat.json_message(job_doc)),
            extra={'job_id': job.id}
        )

        for service in self.services:
            if service == 'deprecate':
                self.publish_job_doc(
                    'deprecate', job.get_deprecate_message()
                )
            elif service == 'create':
                self.publish_job_doc(
                    'create', job.get_create_message()
                )
            elif service == 'obs':
                self.publish_job_doc(
                    'obs', job.get_obs_message()
                )
            elif service == 'publish':
                self.publish_job_doc(
                    'publish', job.get_publish_message()
                )
            elif service == 'replicate':
                self.publish_job_doc(
                    'replicate', job.get_replicate_message()
                )
            elif service == 'test':
                self.publish_job_doc(
                    'test', job.get_test_message()
                )
            elif service == 'upload':
                self.publish_job_doc(
                    'upload', job.get_upload_message()
                )
            elif service == 'raw_image_upload':
                self.publish_job_doc(
                    'raw_image_upload', job.get_raw_image_upload_message()
                )

            if service == job.last_service:
                break

    def start(self):
        """
        Start job creator service.
        """
        self.consume_queue(
            self._handle_service_message,
            self.service_queue,
            self.service_exchange
        )
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def stop(self):
        """
        Stop job creator service.

        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
