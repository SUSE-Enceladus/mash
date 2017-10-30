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
import logging
import pika

# project
from mash.logging_handler import RabbitMQHandler
from mash.exceptions import MashPikaConnectionError


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

        self._open_connection(host)

        self.pika_properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2
        )

        self.host = host
        self.service_exchange = service_exchange
        self.service_key = 'service_event'
        self._declare_topic_exchange(
            self.service_exchange
        )

        logging.basicConfig()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        rabbit_handler = RabbitMQHandler(
            host=self.host,
            routing_key='mash.{level}'
        )
        self.log.addHandler(rabbit_handler)

        self.post_init()

    def post_init(self):
        """
        Post initialization method

        Implementation in specialized service class
        """
        pass

    def publish_service_message(self, message):
        return self._publish(
            self.service_exchange, self.service_key, message
        )

    def publish_listener_message(self, identifier, message):
        return self._publish(
            self.service_exchange, 'listener_{0}'.format(identifier), message
        )

    def bind_service_queue(self):
        return self._bind_queue(
            self.service_exchange, self.service_key
        )

    def bind_listener_queue(self, identifier):
        return self._bind_queue(
            self.service_exchange, 'listener_{0}'.format(identifier)
        )

    def delete_listener_queue(self, identifier):
        self.channel.queue_delete(
            queue='{0}.listener_{1}'.format(self.service_exchange, identifier)
        )

    def consume_queue(self, callback, queue):
        self.channel.basic_consume(
            callback, queue=queue
        )

    def _publish(self, exchange, routing_key, message):
        return self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message,
            properties=self.pika_properties,
            mandatory=True
        )

    def _open_connection(self, host):
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=host)
                )
            except Exception as e:
                raise MashPikaConnectionError(
                    'Connection to RabbitMQ server failed: {0}'.format(e)
                )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.confirm_delivery()

    def close_connection(self):
        try:
            self.connection.close()
        except Exception:
            pass

        self.connection, self.channel = None, None

    def _bind_queue(self, exchange, routing_key):
        self._declare_topic_exchange(exchange)
        declared_queue = self._declare_queue(
            '{0}.{1}'.format(exchange, routing_key)
        )
        self.channel.queue_bind(
            exchange=exchange,
            queue=declared_queue.method.queue,
            routing_key=routing_key
        )
        return declared_queue.method.queue

    def _declare_topic_exchange(self, exchange):
        self.channel.exchange_declare(
            exchange=exchange, exchange_type='topic', durable=True
        )

    def _declare_queue(self, queue):
        return self.channel.queue_declare(queue=queue, durable=True)
