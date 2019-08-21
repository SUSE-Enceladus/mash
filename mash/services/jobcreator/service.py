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
from mash.utils.mash_utils import handle_request


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

        self.set_logfile(self.config.get_log_file(self.service_exchange))
        self.services = self.config.get_service_names()
        self.credentials_url = self.config.get_credentials_url()

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
        Publish delete job message to obs and credentials services.

        This will flush the job with the given id out of the pipeline.
        """
        self.log.info(
            'Deleting job.'.format(job_id),
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

        Message from credentials service contains account info for the
        cloud.
        """
        job = create_job(job_doc)

        self.log.info(
            'Started a new job: {0}'.format(JsonFormat.json_message(job_doc)),
            extra={'job_id': job.id}
        )

        # Credentials job always sent for all jobs.
        try:
            msg = job.get_credentials_message()
            handle_request(
                self.credentials_url,
                'jobs',
                'post',
                msg
            )
        except Exception:
            self.log.error(
                'Failed to send job to credentials service.',
                extra={'job_id': job.id}
            )

        for service in self.services:
            if service == 'deprecation':
                self.publish_job_doc(
                    'deprecation', job.get_deprecation_message()
                )
            elif service == 'obs':
                self.publish_job_doc(
                    'obs', job.get_obs_message()
                )
            elif service == 'publisher':
                self.publish_job_doc(
                    'publisher', job.get_publisher_message()
                )
            elif service == 'replication':
                self.publish_job_doc(
                    'replication', job.get_replication_message()
                )
            elif service == 'testing':
                self.publish_job_doc(
                    'testing', job.get_testing_message()
                )
            elif service == 'uploader':
                self.publish_job_doc(
                    'uploader', job.get_uploader_message()
                )

            if service == job.last_service:
                break

    def start(self):
        """
        Start job creator service.
        """
        self.consume_queue(
            self._handle_service_message,
            queue_name=self.service_queue
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
