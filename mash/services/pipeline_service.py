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

import json
import jwt
import os

from amqpstorm import AMQPError

from apscheduler import events
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from cryptography.fernet import Fernet, MultiFernet
from datetime import datetime, timedelta

from pytz import utc

from mash.services.base_defaults import Defaults
from mash.services.job_factory import JobFactory
from mash.services.mash_service import MashService
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.utils.json_format import JsonFormat


class PipelineService(MashService):
    """
    Base class for MASH services that live in the image pipeline.
    """
    def post_init(self):
        """Initialize base service class and job scheduler."""
        self.listener_queue = 'listener'
        self.service_queue = 'service'
        self.job_document_key = 'job_document'
        self.listener_msg_key = 'listener_msg'

        self.jobs = {}

        # setup service job directory
        self.job_directory = Defaults.get_job_directory(self.service_exchange)
        os.makedirs(
            self.job_directory, exist_ok=True
        )

        self.next_service = self._get_next_service()
        self.prev_service = self._get_previous_service()

        # Credentials config
        self.encryption_keys_file = self.config.get_encryption_keys_file()
        self.jwt_secret = self.config.get_jwt_secret()
        self.jwt_algorithm = self.config.get_jwt_algorithm()

        self.credentials_queue = 'credentials'
        self.credentials_response_key = 'response'
        self.credentials_request_key = 'request.{0}'.format(
            self.service_exchange
        )

        if not self.custom_args:
            self.custom_args = {}

        self.listener_msg_args = []
        self.status_msg_args = ['cloud_image_name']

        if self.custom_args.get('listener_msg_args'):
            self.listener_msg_args += self.custom_args['listener_msg_args']

        if self.custom_args.get('status_msg_args'):
            self.status_msg_args += self.custom_args['status_msg_args']

        self.set_logfile(self.config.get_log_file(self.service_exchange))

        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )
        self.bind_queue(
            self.service_exchange, self.listener_msg_key, self.listener_queue
        )
        self.bind_credentials_queue()

        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.add_listener(
            self._process_job_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

        self.restart_jobs(self._add_job)
        self.start()

    def _add_job(self, job_config):
        """
        Create job using job factory if job id does not already exist.

        Job config is persisted to disk if not already done.
        """
        job_id = job_config['id']
        cloud = job_config['cloud']

        if job_id not in self.jobs:
            try:
                job = JobFactory.create_job(
                    cloud, self.service_exchange, job_config, self.config
                )
            except Exception as error:
                self.log.error(
                    'Invalid job: {0}.'.format(error)
                )
            else:
                self.jobs[job.id] = job
                job.log_callback = self.log_job_message

                if 'job_file' not in job_config:
                    job_config['job_file'] = self.persist_job_config(
                        job_config
                    )
                    job.job_file = job_config['job_file']

                self.log.info(
                    'Job queued, awaiting listener message.',
                    extra=job.get_job_id()
                )
        else:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )

    def _cleanup_job(self, job, status):
        """
        Job failed upstream.

        Delete job and notify the next service.
        """
        job.status = status
        self.log.warning('Failed upstream.', extra=job.get_job_id())

        try:
            # Remove job from scheduler if it has
            # not started executing yet.
            self.scheduler.remove_job(job.id)
        except JobLookupError:
            pass

        self._delete_job(job.id)

        if job.last_service != self.service_exchange:
            self._publish_message(job)

    def _delete_job(self, job_id):
        """
        Remove job from dict and delete listener queue.
        """
        if job_id in self.jobs:
            job = self.jobs[job_id]
            self.log.info(
                'Deleting job.',
                extra=job.get_job_id()
            )

            if job.last_service == self.service_exchange:
                # Send delete message to credentials
                # if this is the last service.
                self.publish_credentials_delete(job_id)

            del self.jobs[job_id]
            self.remove_file(job.job_file)
        else:
            self.log.warning(
                'Job deletion failed, job is not queued.',
                extra={'job_id': job_id}
            )

    def _get_next_service(self):
        """Return the next service based on the current exchange."""
        services = self.config.get_service_names()

        try:
            next_service = services[services.index(self.service_exchange) + 1]
        except (IndexError, ValueError):
            next_service = None

        return next_service

    def _get_previous_service(self):
        """
        Return the previous service based on the current exchange.
        """
        services = self.config.get_service_names()

        try:
            index = services.index(self.service_exchange) - 1
        except ValueError:
            return None

        if index < 0:
            return None

        return services[index]

    def _get_status_message(self, job):
        """
        Build and return json message.

        Message contains completion status to post to next service exchange.
        """
        key = '{0}_result'.format(self.service_exchange)

        data = {
            key: {
                'id': job.id,
                'status': job.status,
            }
        }

        if job.status == SUCCESS:
            for arg in self.status_msg_args:
                data[key][arg] = getattr(job, arg)

        return JsonFormat.json_message(data)

    def _handle_credentials_response(self, message):
        """
        Process credentials response JWT tokens.
        """
        try:
            token = json.loads(message.body)
        except Exception:
            self.log.error(
                'Invalid credentials response message: '
                'Must be a json encoded message.'
            )
        else:
            job_id, credentials = self.decode_credentials(token)
            job = self.jobs.get(job_id)

            if job:
                job.credentials = credentials
                self._schedule_job(job.id)
            elif job_id:
                self.log.error(
                    'Credentials received for invalid job with ID:'
                    ' {0}.'.format(job_id)
                )

        message.ack()

    def _handle_listener_message(self, message):
        """
        Callback for listener messages.
        """
        job = self._validate_listener_msg(message.body)

        if job:
            job.listener_msg = message

            if job.credentials:
                self._schedule_job(job.id)
            else:
                self.publish_credentials_request(job.id)
        else:
            message.ack()

    def _handle_service_message(self, message):
        """
        Callback for events from jobcreator.
        """
        job_key = '{0}_job'.format(self.service_exchange)
        try:
            job_desc = json.loads(message.body)
            self._add_job(job_desc[job_key])
        except Exception as e:
            self.log.error('Error adding job: {0}.'.format(e))

        message.ack()

    def _process_job_result(self, event):
        """
        Callback when job background process finishes.

        Handle exceptions and errors that occur and logs info to job log.
        """
        job_id = event.job_id
        job = self.jobs[job_id]
        metadata = job.get_job_id()

        if job.utctime != 'always':
            self._delete_job(job_id)

        if event.exception:
            job.status = EXCEPTION
            self.log.error(
                'Pass[{0}]: Exception in {1}: {2}'.format(
                    job.iteration_count,
                    self.service_exchange,
                    event.exception
                ),
                extra=metadata
            )
        elif job.status == SUCCESS:
            self.log.info(
                'Pass[{0}]: {1} successful.'.format(
                    job.iteration_count,
                    self.service_exchange
                ),
                extra=metadata
            )
        else:
            self.log.error(
                'Pass[{0}]: Error occurred in {1}.'.format(
                    job.iteration_count,
                    self.service_exchange
                ),
                extra=metadata
            )

        # Don't send failure messages for always jobs and
        # don't send message if last service.
        if (job.utctime != 'always' or job.status == SUCCESS) \
                and job.last_service != self.service_exchange:
            self._publish_message(job)

        self.send_email_notification(
            job.id, job.notification_email, job.notification_type, job.status,
            job.utctime, job.last_service, job.iteration_count,
            event.exception
        )

        job.listener_msg.ack()

    def _publish_message(self, job):
        """
        Publish status message to next service exchange.
        """
        message = self._get_status_message(job)
        try:
            self.publish_job_result(self.next_service, message)
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(message),
                extra=job.get_job_id()
            )

    def _schedule_job(self, job_id):
        """
        Schedule new job in background scheduler for job based on id.
        """
        try:
            self.scheduler.add_job(
                self._start_job,
                args=(job_id,),
                id=job_id,
                max_instances=1,
                misfire_grace_time=None,
                coalesce=True
            )
        except ConflictingIdError:
            self.log.warning(
                'Job already running. Received multiple '
                'listener messages.',
                extra={'job_id': job_id}
            )

    def _start_job(self, job_id):
        """
        Process job based on job id.
        """
        job = self.jobs[job_id]
        job.process_job()

    def _validate_listener_msg(self, message):
        """
        Validate the required keys are in message dictionary.

        If listener message is valid return the job instance.
        """
        listener_msg = self._get_listener_msg(
            message,
            '{0}_result'.format(self.prev_service)
        )

        if not listener_msg:
            return None

        if self._validate_base_msg(listener_msg, self.listener_msg_args):
            job = self.jobs[listener_msg['id']]

            for arg in self.listener_msg_args:
                self._process_msg_arg(listener_msg, arg, job)

            return job
        else:
            return None

    def _get_listener_msg(self, message, key):
        """Load json and attempt to get message by key."""
        try:
            listener_msg = json.loads(message)[key]
        except Exception:
            self.log.error(
                'Invalid listener message: {0}'.format(message)
            )
            listener_msg = None

        return listener_msg

    def _validate_base_msg(self, listener_msg, args):
        """
        Validate the base message.

        - Message should have an id and status.
        - The job should exist.
        - The status should be success.
        """
        for arg in ['id', 'status']:
            if arg not in listener_msg:
                self.log.error('{0} is required in listener message.'.format(arg))
                return False

        if listener_msg['id'] not in self.jobs:
            self.log.error(
                'Invalid listener message with id: {0}.'.format(
                    listener_msg['id']
                )
            )
            return False

        status = listener_msg['status']
        if status != SUCCESS:
            job = self.jobs[listener_msg['id']]
            self._cleanup_job(job, status)
            return False

        for arg in args:
            if arg not in listener_msg:
                self.log.error('{0} is required in listener message.'.format(arg))
                return False

        return True

    def _process_msg_arg(self, listener_msg, arg, job):
        """Set the arg on the job using setter method."""
        setattr(job, arg, listener_msg[arg])

    def bind_credentials_queue(self):
        """
        Bind the response key to the credentials queue.
        """
        self.bind_queue(
            self.service_exchange,
            self.credentials_response_key,
            self.credentials_queue
        )

    def consume_credentials_queue(self, callback):
        """
        Setup credentials attributes from configuration.

        Then consume credentials response queue to receive credentials
        tokens for jobs.
        """
        queue_name = self.credentials_queue
        queue = self._get_queue_name(self.service_exchange, queue_name)
        self.channel.basic.consume(callback=callback, queue=queue)

    def decode_credentials(self, message):
        """
        Decode jwt credential response message.
        """
        decrypted_credentials = {}
        try:
            payload = jwt.decode(
                message['jwt_token'], self.jwt_secret,
                algorithm=self.jwt_algorithm, issuer='credentials',
                audience=self.service_exchange
            )
            job_id = payload['id']
            for account, credentials in payload['credentials'].items():
                decrypted_credentials[account] = self.decrypt_credentials(
                    credentials
                )
        except KeyError as error:
            self.log.error(
                'Invalid credentials response recieved: {0}'
                ' key must be in credentials message.'.format(error)
            )
        except Exception as error:
            self.log.error(
                'Invalid credentials response token: {0}'.format(error)
            )
        else:
            return job_id, decrypted_credentials

        # If exception occurs decoding credentials return None.
        return None, None

    def decrypt_credentials(self, credentials):
        """
        Decrypt credentials string and load json to dictionary.
        """
        encryption_keys = self.get_encryption_keys_from_file(
            self.encryption_keys_file
        )
        fernet_key = MultiFernet(encryption_keys)

        try:
            # Ensure string is encoded as bytes before decrypting.
            credentials = credentials.encode()
        except Exception:
            pass

        return json.loads(fernet_key.decrypt(credentials).decode())

    def get_credential_request(self, job_id):
        """
        Return jwt encoded credentials request message.
        """
        request = {
            'exp': datetime.utcnow() + timedelta(minutes=5),  # Expiration time
            'iat': datetime.utcnow(),  # Issued at time
            'sub': 'credentials_request',  # Subject
            'iss': self.service_exchange,  # Issuer
            'aud': 'credentials',  # audience
            'id': job_id,
        }
        token = jwt.encode(
            request, self.jwt_secret, algorithm=self.jwt_algorithm
        )
        message = json.dumps({'jwt_token': token.decode()})
        return message

    def get_encryption_keys_from_file(self, encryption_keys_file):
        """
        Returns a list of Fernet keys based on the provided keys file.
        """
        with open(encryption_keys_file, 'r') as keys_file:
            keys = keys_file.readlines()

        return [Fernet(key.strip()) for key in keys if key]

    def publish_credentials_delete(self, job_id):
        """
        Publish delete message to credentials service.
        """
        delete_message = JsonFormat.json_message(
            {"credentials_job_delete": job_id}
        )

        try:
            self._publish(
                'credentials', self.job_document_key, delete_message
            )
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(delete_message)
            )

    def publish_credentials_request(self, job_id):
        """
        Publish credentials request message to the credentials exchange.
        """
        self._publish(
            'credentials', self.credentials_request_key,
            self.get_credential_request(job_id)
        )

    def publish_job_result(self, exchange, message):
        """
        Publish the result message to the listener queue on given exchange.
        """
        self._publish(exchange, self.listener_msg_key, message)

    def log_job_message(self, msg, metadata, success=True):
        """
        Callback for job instance to log given message.
        """
        if success:
            self.log.info(msg, extra=metadata)
        else:
            self.log.error(msg, extra=metadata)

    def remove_file(self, config_file):
        """
        Remove file from disk if it exists.
        """
        try:
            os.remove(config_file)
        except Exception:
            pass

    def start(self):
        """
        Start pipeline service.
        """
        self.scheduler.start()
        self.consume_queue(
            self._handle_service_message,
            queue_name=self.service_queue
        )
        self.consume_queue(
            self._handle_listener_message,
            queue_name=self.listener_queue
        )
        self.consume_credentials_queue(self._handle_credentials_response)

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.scheduler.shutdown()
            self.close_connection()
