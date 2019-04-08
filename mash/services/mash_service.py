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
import jwt
import logging
import os
import smtplib

from amqpstorm import AMQPError, Connection
from cryptography.fernet import Fernet, MultiFernet
from datetime import datetime, timedelta
from email.message import EmailMessage

# project
from mash.log.filter import BaseServiceFilter
from mash.log.handler import RabbitMQHandler
from mash.services.base_defaults import Defaults
from mash.services import get_configuration
from mash.services.status_levels import SUCCESS
from mash.mash_exceptions import (
    MashRabbitConnectionException,
    MashLogSetupException
)
from mash.utils.json_format import JsonFormat


class MashService(object):
    """
    Base class for RabbitMQ message broker

    Attributes

    * :attr:`host`
      RabbitMQ server host

    * :attr:`service_exchange`
      Name of service exchange
    """
    def __init__(self, service_exchange):
        self.channel = None
        self.connection = None

        self.service_exchange = service_exchange
        self.service_queue = 'service'
        self.listener_queue = 'listener'
        self.job_document_key = 'job_document'
        self.listener_msg_key = 'listener_msg'

        self.config = get_configuration(self.service_exchange)
        self.next_service = self._get_next_service()
        self.prev_service = self._get_previous_service()
        self.encryption_keys_file = self.config.get_encryption_keys_file()
        self.jwt_secret = self.config.get_jwt_secret()
        self.jwt_algorithm = self.config.get_jwt_algorithm()

        # amqp settings
        self.amqp_host = self.config.get_amqp_host()
        self.amqp_user = self.config.get_amqp_user()
        self.amqp_pass = self.config.get_amqp_pass()

        # smtp settings
        self.smtp_host = self.config.get_smtp_host()
        self.smtp_port = self.config.get_smtp_port()
        self.smtp_ssl = self.config.get_smtp_ssl()
        self.smtp_user = self.config.get_smtp_user()
        self.smtp_pass = self.config.get_smtp_pass()
        self.notification_subject = self.config.get_notification_subject()

        # setup service data directory
        self.job_directory = Defaults.get_job_directory(self.service_exchange)
        os.makedirs(
            self.job_directory, exist_ok=True
        )

        self._open_connection()
        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )
        self.bind_queue(
            self.service_exchange, self.listener_msg_key, self.listener_queue
        )

        # Credentials
        self.credentials_queue = 'credentials'
        self.credentials_response_key = 'response'
        self.credentials_request_key = 'request.{0}'.format(
            self.service_exchange
        )

        self.add_account_key = 'add_account'
        self.delete_account_key = 'delete_account'

        logging.basicConfig()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False

        rabbit_handler = RabbitMQHandler(
            host=self.amqp_host,
            username=self.amqp_user,
            password=self.amqp_pass,
            routing_key='mash.logger'
        )
        rabbit_handler.setFormatter(
            logging.Formatter(
                '%(newline)s%(levelname)s %(asctime)s %(name)s%(newline)s'
                '    %(job)s %(message)s%(newline)s'
            )
        )
        self.log.addHandler(rabbit_handler)
        self.log.addFilter(BaseServiceFilter())

        self.post_init()

    def post_init(self):
        """
        Post initialization method

        Implementation in specialized service class
        """
        pass

    def _declare_direct_exchange(self, exchange):
        """
        Declare/create exchange and set as durable.

        The exchange, queues and messages will survive a broker restart.
        """
        self.channel.exchange.declare(
            exchange=exchange, exchange_type='direct', durable=True
        )

    def _declare_queue(self, queue):
        """
        Declare the queue and set as durable.
        """
        return self.channel.queue.declare(queue=queue, durable=True)

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

    def _get_queue_name(self, exchange, name):
        """
        Return formatted name based on exchange and queue name.

        Example: obs.service
        """
        return '{0}.{1}'.format(exchange, name)

    def _open_connection(self):
        """
        Open connection or channel if currently closed or None.

        Raises: MashRabbitConnectionException if connection
                cannot be established.
        """
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = Connection(
                    self.amqp_host,
                    self.amqp_user,
                    self.amqp_pass,
                    kwargs={'heartbeat': 600}
                )
            except Exception as e:
                raise MashRabbitConnectionException(
                    'Connection to RabbitMQ server failed: {0}'.format(e)
                )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.confirm_deliveries()

    def _publish(self, exchange, routing_key, message):
        """
        Publish message to the provided exchange with the routing key.
        """
        self.channel.basic.publish(
            body=message,
            routing_key=routing_key,
            exchange=exchange,
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            },
            mandatory=True
        )

    def bind_credentials_queue(self):
        """
        Bind the response key to the credentials queue.
        """
        self.bind_queue(
            self.service_exchange, self.credentials_response_key,
            self.credentials_queue
        )

    def bind_queue(self, exchange, routing_key, name):
        """
        Bind queue on exchange to the provided routing key.

        All messages that match the routing key will be inserted in queue.
        """
        self._declare_direct_exchange(exchange)
        queue = self._get_queue_name(exchange, name)
        self._declare_queue(queue)
        self.channel.queue.bind(
            exchange=exchange, queue=queue, routing_key=routing_key
        )
        return queue

    def close_connection(self):
        """
        If channel or connection open, stop consuming and close.
        """
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def consume_credentials_queue(self, callback, queue_name=None):
        """
        Setup credentials attributes from configuration.

        Then consume credentials response queue to receive credentials
        tokens for jobs.
        """
        if not queue_name:
            queue_name = self.credentials_queue

        queue = self._get_queue_name(self.service_exchange, queue_name)
        self.channel.basic.consume(callback=callback, queue=queue)

    def consume_queue(self, callback, queue_name=None):
        """
        Declare and consume queue.

        If queue_name not provided use service_queue name attr.
        """
        if not queue_name:
            queue_name = self.service_queue

        queue = self._get_queue_name(self.service_exchange, queue_name)
        self._declare_queue(queue)
        self.channel.basic.consume(
            callback=callback, queue=queue
        )

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

    def encrypt_credentials(self, credentials):
        """
        Encrypt credentials json string.

        Returns: Encrypted and decoded string.
        """
        encryption_keys = self.get_encryption_keys_from_file(
            self.encryption_keys_file
        )
        fernet = MultiFernet(encryption_keys)

        try:
            # Ensure creds string is encoded as bytes
            credentials = credentials.encode()
        except Exception:
            pass

        return fernet.encrypt(credentials).decode()

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

    def log_job_message(self, msg, metadata, success=True):
        """
        Callback for job instance to log given message.
        """
        if success:
            self.log.info(msg, extra=metadata)
        else:
            self.log.error(msg, extra=metadata)

    def persist_job_config(self, config):
        """
        Persist the job config file to disk for recoverability.
        """
        config['job_file'] = '{0}job-{1}.json'.format(
            self.job_directory, config['id']
        )

        with open(config['job_file'], 'w') as config_file:
            config_file.write(JsonFormat.json_message(config))

        return config['job_file']

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

    def remove_file(self, config_file):
        """
        Remove file from disk if it exists.
        """
        try:
            os.remove(config_file)
        except Exception:
            pass

    def restart_jobs(self, callback):
        """
        Restart jobs from config files.

        Recover from service failure with existing jobs.
        """
        for job_file in os.listdir(self.job_directory):
            with open(os.path.join(self.job_directory, job_file), 'r') \
                    as conf_file:
                job_config = json.load(conf_file)

            callback(job_config)

    def set_logfile(self, logfile):
        """
        Allow to set a custom service log file
        """
        try:
            log_dir = os.path.dirname(logfile)
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)

            logfile_handler = logging.FileHandler(
                filename=logfile, encoding='utf-8'
            )
            self.log.addHandler(logfile_handler)
        except Exception as e:
            raise MashLogSetupException(
                'Log setup failed: {0}'.format(e)
            )

    def unbind_queue(self, queue, exchange, routing_key):
        """
        Unbind the routing_key from the queue on given exchange.
        """
        queue = self._get_queue_name(exchange, queue)
        self.channel.queue.unbind(
            queue=queue, exchange=exchange, routing_key=routing_key
        )

    def _create_email_message(self, msg, subject, to_email, from_email):
        """
        Return notification email message object.
        """
        email_msg = EmailMessage()

        email_msg['Subject'] = subject
        email_msg['From'] = from_email
        email_msg['To'] = to_email

        email_msg.set_content(msg)

        return email_msg

    def send_email(self, email_msg):
        """
        Send email message using smtp server.

        :param email_msg:  email.message.EmailMessage
        """
        if self.smtp_ssl:
            smtp_class = smtplib.SMTP_SSL
        else:
            smtp_class = smtplib.SMTP

        try:
            smtp_server = smtp_class(self.smtp_host, self.smtp_port)

            if self.smtp_user and self.smtp_pass:
                smtp_server.login(self.smtp_user, self.smtp_pass)

            smtp_server.send_message(email_msg)
        except Exception as error:
            self.log.warning(
                'Unable to send notification email: {0}'.format(error)
            )

    def _should_notify(
        self, notification_email, notification_type, utctime, status,
        last_service
    ):
        """
        Return True if a notification email should be sent based on job info.
        """
        if not notification_email:
            return False
        elif status != SUCCESS:
            return True
        elif notification_type == 'periodic' and utctime != 'always':
            return True
        elif last_service == self.service_exchange and utctime != 'always':
            return True

        return False

    def _create_notification_content(
        self, job_id, status, utctime, last_service,
        iteration_count=None, error=None
    ):
        """
        Build content string for body of job notification email.
        """
        msg = [
            'Job: {job_id}\n'
            'Service: {service}\n'
            'Log: {job_log}\n\n'
        ]

        if status == SUCCESS:
            if self.service_exchange == last_service:
                msg.append('Job finished successfully.')
            else:
                msg.append(
                    'Job finished through the {service} service.'
                )
        else:
            msg.append('Job failed.')

            if utctime == 'always' and iteration_count:
                msg.append(' The current pass is #{iteration_count}.')

            if error:
                msg.append(' The following error was logged: \n\n{error}')

        msg = ''.join(msg)

        return msg.format(
            job_id=job_id,
            service=self.service_exchange,
            job_log=self.config.get_job_log_file(job_id),
            iteration_count=str(iteration_count),
            error=error
        )

    def send_email_notification(
        self, job_id, notification_email, notification_type, status, utctime,
        last_service, iteration_count=None, error=None
    ):
        """
        Send job notification email based on result of _should_notify.
        """
        notify = self._should_notify(
            notification_email, notification_type, utctime, status,
            last_service
        )

        if notify:
            content = self._create_notification_content(
                job_id, status, utctime, last_service, iteration_count, error
            )
            email_msg = self._create_email_message(
                msg=content,
                subject=self.notification_subject,
                to_email=notification_email,
                from_email=self.smtp_user
            )
            self.send_email(email_msg)
