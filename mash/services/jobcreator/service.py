# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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
from mash.services.status_levels import SUCCESS
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import setup_logfile
from mash.utils.mash_utils import handle_request
from mash.utils.email_notification import EmailNotification


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
        self.database_api_url = self.config.get_database_api_url()

        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )
        self._bind_result_queues()

        # notification settings
        self.notification_class = EmailNotification(
            self.config.get_smtp_host(),
            self.config.get_smtp_port(),
            self.config.get_smtp_user(),
            self.config.get_smtp_pass(),
            self.config.get_smtp_ssl(),
            log_callback=self.log
        )

        self.start()

    def _bind_result_queues(self):
        for service in self.services:
            self.bind_queue(
                service,
                'listener_msg',
                '{service}_status'.format(service=service)
            )

    def _handle_service_message(self, message):
        """
        Handle new job messages.
        """
        try:
            job_doc = json.loads(message.body)
            self.send_job(job_doc)
        except Exception as error:
            self.log.error(
                'Invalid message received: {0}.'.format(error)
            )

        message.ack()

    def _handle_status_message(self, message):
        """
        Handle status messages from listener services.
        """
        job_doc = None

        try:
            job_doc = json.loads(message.body)
        except Exception as error:
            self.log.error(
                'Invalid message received: {0}.'.format(error)
            )

        if job_doc:
            for key, value in job_doc.items():
                service = key.rsplit('_', maxsplit=1)[0]

                if service not in self.services:
                    self.log.warning(
                        'Unkown service message received for {0} service.'.format(
                            service
                        )
                    )
                else:
                    self._process_job_status(service, value)

        message.ack()

    def _get_next_service(self, service):
        """
        Return the next service based on the service name.
        """
        index = self.services.index(service)

        if index >= len(self.services) - 1:
            return None

        return self.services[index + 1]

    def _process_job_status(self, service, job_doc):
        """
        Send job status to DB service.

        Include info on prev and next service which DB service
        does not know about.
        """
        job_doc['current_service'] = self._get_next_service(service)
        job_doc['prev_service'] = service
        last_service = job_doc.pop('last_service')
        notification_email = job_doc.pop('notification_email')

        try:
            handle_request(
                self.database_api_url,
                'jobs/',
                'put',
                job_data=job_doc
            )
        except Exception as error:
            self.log.error('Job status update failed: {}'.format(error))

        if notification_email and (last_service == service):
            self.send_notification(
                job_doc['id'],
                notification_email,
                job_doc['status'],
                job_doc.get('cloud_image_name'),
                job_doc.get('blob_name'),
                job_doc['errors']
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
            elif service == 'download':
                self.publish_job_doc(
                    'download', job.get_download_message()
                )
            elif service == 'publish':
                self.publish_job_doc(
                    'publish', job.get_publish_message()
                )
            elif service == 'replicate':
                self.publish_job_doc(
                    'replicate', job.get_replicate_message()
                )
            elif service == 'test_preparation':
                self.publish_job_doc(
                    'test_preparation', job.get_test_preparation_message()
                )
            elif service == 'test':
                self.publish_job_doc(
                    'test', job.get_test_message()
                )
            elif service == 'test_cleanup':
                self.publish_job_doc(
                    'test_cleanup', job.get_test_cleanup_message()
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

    def _create_notification_content(
        self,
        job_id,
        status,
        image_name,
        blob_name,
        errors=None
    ):
        """
        Build content string for job notification message.
        """
        msg = [
            f'Job: {job_id}\n'
        ]
        error_msg = ''

        if image_name:
            msg.append(f'Image Name: {image_name}\n')
        elif blob_name:
            msg.append(f'Blob Name: {blob_name}\n')

        if status == SUCCESS:
            msg.append('Job finished successfully.')
        else:
            msg.append('Job failed.')

            if errors:
                error_msg = '\n\n'.join(errors)
                msg.append(f' The following errors were logged: \n\n{error_msg}')

        msg = ''.join(msg)

        return msg

    def send_notification(
        self,
        job_id,
        notification_email,
        status,
        image_name,
        blob_name,
        errors=None
    ):
        """
        Send job notification based on result of _should_notify.
        """
        content = self._create_notification_content(
            job_id,
            status,
            image_name,
            blob_name,
            errors
        )
        self.notification_class.send_notification(
            content,
            self.config.get_notification_subject(),
            notification_email
        )

    def start(self):
        """
        Start job creator service.
        """
        self.consume_queue(
            self._handle_service_message,
            self.service_queue,
            self.service_exchange
        )

        for service in self.services:
            self.consume_queue(
                self._handle_status_message,
                '{service}_status'.format(service=service),
                service
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
