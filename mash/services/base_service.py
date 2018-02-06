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

import json
import jwt
import logging
import os

from amqpstorm import Connection
from datetime import datetime, timedelta

# project
from mash.log.filter import BaseServiceFilter
from mash.log.handler import RabbitMQHandler
from mash.services.base_defaults import Defaults
from mash.services.credentials.amazon import CredentialsAmazon
from mash.mash_exceptions import (
    MashCredentialsException,
    MashRabbitConnectionException,
    MashLogSetupException
)


class BaseService(object):
    """
    Base class for RabbitMQ message broker

    Attributes

    * :attr:`host`
      RabbitMQ server host

    * :attr:`service_exchange`
      Name of service exchange
    """
    def __init__(self, host, service_exchange):
        self.channel = None
        self.connection = None

        self.msg_properties = {
            'content_type': 'application/json',
            'delivery_mode': 2
        }

        self.host = host
        self.service_exchange = service_exchange
        self.service_queue = 'service'
        self.listener_queue = 'listener'
        self.job_document_key = 'job_document'

        # setup service data directory
        self.job_directory = Defaults.get_job_directory(self.service_exchange)
        os.makedirs(
            self.job_directory, exist_ok=True
        )

        self._open_connection()
        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )

        # Credentials
        self.credentials_queue = 'credentials'
        self.credentials_key = 'credentials_response'

        self.bind_queue(
            self.service_exchange, self.credentials_key, self.credentials_queue
        )

        logging.basicConfig()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False

        rabbit_handler = RabbitMQHandler(
            host=self.host,
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

    def set_logfile(self, logfile):
        """
        Allow to set a custom service log file
        """
        try:
            logfile_handler = logging.FileHandler(
                filename=logfile, encoding='utf-8'
            )
            self.log.addHandler(logfile_handler)
        except Exception as e:
            raise MashLogSetupException(
                'Log setup failed: {0}'.format(e)
            )

    def publish_job_result(self, exchange, job_id, message):
        self.bind_queue(exchange, job_id, self.service_queue)
        self._publish(exchange, job_id, message)

    def consume_queue(self, callback, queue_name=None):
        if not queue_name:
            queue_name = self.service_queue
        queue = self._get_queue_name(self.service_exchange, queue_name)
        self._declare_queue(queue)
        self.channel.basic.consume(
            callback=callback, queue=queue
        )

    def publish_credentials_result(self, job_id, csp, message):
        """Deprecated"""
        exchange = 'credentials'
        self.bind_queue(exchange, job_id, csp)
        self._publish(exchange, job_id, message)

    def consume_credentials_queue(self, callback):
        """
        Setup credentials attributes from configuration.

        Then consume credentials response queue to receive credentials
        tokens for jobs.
        """
        # Required by all services that need credentials.
        # Config is not available until post init.
        self.jwt_secret = self.config.get_jwt_secret()
        self.jwt_algorithm = self.config.get_jwt_algorithm()

        queue = self._get_queue_name(
            self.service_exchange, self.credentials_queue
        )
        self.channel.basic.consume(callback=callback, queue=queue)

    def bind_credentials_queue(self, job_id, csp):
        """Deprecated"""
        self.bind_queue('credentials', job_id, csp)

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
        return jwt.encode(
            request, self.jwt_secret, algorithm=self.jwt_algorithm
        )

    def decode_credentials(self, message, provider):
        """
        Decode jwt credential response message.
        """
        try:
            payload = jwt.decode(
                message, self.jwt_secret, algorithm=self.jwt_algorithm,
                issuer='credentials', audience=self.service_exchange
            )
        except Exception as error:
            raise MashCredentialsException(
                'Invalid credentials response token: {0}'.format(error)
            )

        try:
            credentials = payload['credentials']
        except KeyError:
            raise MashCredentialsException(
                'Credentials not found in payload.'
            )

        if provider == 'ec2':
            provider_class = CredentialsAmazon

        accounts = {}
        for name, credential in credentials.items():
            accounts[name] = provider_class(custom_args=credential)

        return accounts

    def publish_credentials_request(self, job_id):
        self._publish(
            'credentials', 'request.{0}'.format(self.service_exchange),
            self.get_credential_request(job_id)
        )

    def close_connection(self):
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def _get_queue_name(self, exchange, name):
        return '{0}.{1}'.format(exchange, name)

    def _publish(self, exchange, routing_key, message):
        self.channel.basic.publish(
            body=message,
            routing_key=routing_key,
            exchange=exchange,
            properties=self.msg_properties,
            mandatory=True
        )

    def _open_connection(self):
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = Connection(
                    self.host,
                    'guest',
                    'guest',
                    kwargs={'heartbeat': 600}
                )
            except Exception as e:
                raise MashRabbitConnectionException(
                    'Connection to RabbitMQ server failed: {0}'.format(e)
                )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.confirm_deliveries()

    def bind_queue(self, exchange, routing_key, name):
        self._declare_direct_exchange(exchange)
        queue = self._get_queue_name(exchange, name)
        self._declare_queue(queue)
        self.channel.queue.bind(
            exchange=exchange, queue=queue, routing_key=routing_key
        )
        return queue

    def _declare_direct_exchange(self, exchange):
        self.channel.exchange.declare(
            exchange=exchange, exchange_type='direct', durable=True
        )

    def _declare_queue(self, queue):
        return self.channel.queue.declare(queue=queue, durable=True)

    def persist_job_config(self, config):
        config['job_file'] = '{0}job-{1}.json'.format(
            self.job_directory, config['id']
        )

        with open(config['job_file'], 'w') as config_file:
            config_file.write(json.dumps(config, sort_keys=True))

        return config['job_file']

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

    def bind_listener_queue(self, routing_key):
        self.bind_queue(
            self.service_exchange, routing_key, self.listener_queue
        )

    def unbind_queue(self, queue, exchange, routing_key):
        self.channel.queue.unbind(
            queue=queue, exchange=exchange, routing_key=routing_key
        )
