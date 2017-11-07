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
import os
import pika

from datetime import datetime
from logging.handlers import SocketHandler


class RabbitMQHandler(SocketHandler):
    """
    Log handler for sending messages to RabbitMQ.
    """
    def __init__(
        self, host='localhost', port=5672, exchange='logger',
        username='guest', password='guest',
        routing_key='logger.{level}'
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
        rabbit_attrs = ['msg', 'levelname', 'name', 'job_id']

        data = {}
        self.format(record)

        for attr in rabbit_attrs:
            if hasattr(record, attr):
                data[attr] = getattr(record, attr)

        if hasattr(record, 'exc_info') and record.exc_info:
            data['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(data)

    def format(self, record):
        TEMPLATE = '{levelname} {timestamp} {name}{newline}' \
                   '    {msg}{newline}'

        record.timestamp = datetime.now().isoformat(' ')
        record.newline = os.linesep
        record.msg = TEMPLATE.format(**record.__dict__)


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
        if self.channel:
            self.channel.close()

        if self.connection:
            self.connection.close()

    def declare_exchange(self):
        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='topic',
            durable=True
        )

    def open(self):
        """"
        Create/open connection and declare logging exchange.
        """
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    heartbeat_interval=600
                )
            )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()

    def sendall(self, msg):
        """
        Override socket sendall method to publish message to exchange.
        """
        level = json.loads(msg)['levelname']

        self.open()
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key.format(level=level),
            body=msg,
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2
            )
        )
