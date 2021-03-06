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

from amqpstorm import Connection

from logging.handlers import SocketHandler


class RabbitMQHandler(SocketHandler):
    """
    Log handler for sending messages to RabbitMQ.
    """
    def __init__(
        self, host='localhost', port=5672, exchange='logger',
        username='guest', password='guest',
        routing_key='mash.logger'
    ):
        """
        Initialize the handler instance.
        """
        super(RabbitMQHandler, self).__init__(host, port)

        self.username = username
        self.password = password
        self.exchange = exchange
        self.routing_key = routing_key

    def makeSocket(self):
        """
        Create a new instance of RabbitMQ socket connection.
        """
        return RabbitMQSocket(
            self.host,
            self.port,
            self.username,
            self.password,
            self.exchange,
            self.routing_key
        )

    def makePickle(self, record):
        """
        Format the log message to a json string.
        """
        rabbit_attrs = ['msg', 'job_id']

        data = {}
        record.msg = self.format(record)

        for attr in rabbit_attrs:
            if hasattr(record, attr):
                data[attr] = getattr(record, attr)

        return json.dumps(data, sort_keys=True)


class RabbitMQSocket(object):
    """
    RabbitMQ socket class.

    Maintains a connection for logging and publishing
    logs to exchange.
    """
    def __init__(
        self, host, port, username, password, exchange, routing_key
    ):
        """
        Initialize RabbitMQ socket instance.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.exchange = exchange
        self.routing_key = routing_key
        self.connection = None
        self.channel = None
        self.open()
        self.declare_exchange()

    def close(self):
        """
        Close socket connection.
        """
        if self.channel and self.channel.is_open:
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def declare_exchange(self):
        self.channel.exchange.declare(
            exchange=self.exchange,
            exchange_type='direct',
            durable=True
        )

    def open(self):
        """"
        Create/open connection and declare logging exchange.
        """
        if not self.connection or self.connection.is_closed:
            self.connection = Connection(
                self.host,
                self.username,
                self.password,
                port=self.port,
                kwargs={'heartbeat': 600}
            )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()

    def sendall(self, msg):
        """
        Override socket sendall method to publish message to exchange.
        """
        self.open()
        self.channel.basic.publish(
            body=msg,
            routing_key=self.routing_key,
            exchange=self.exchange,
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            }
        )
