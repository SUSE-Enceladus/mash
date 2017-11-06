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

        for attr in rabbit_attrs:
            if hasattr(record, attr):
                data[attr] = getattr(record, attr)

        data['timestamp'] = datetime.now().isoformat(' ')

        if hasattr(record, 'args') and record.args:
            data['msg'] = data['msg'] % record.args

        if hasattr(record, 'exc_info') and record.exc_info:
            data['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(data)


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

    def close(self):
        """
        Close socket connection.
        """
        try:
            self.connection.close()
        except Exception:
            pass

    def open(self):
        """"
        Create/open connection and declare logging exchange.
        """
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port
            )
        )
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='topic',
            durable=True
        )

    def sendall(self, msg):
        """
        Override socket sendall method to publish message to exchange.
        """
        level = json.loads(msg)['levelname']
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key.format(level=level),
            body=msg,
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2
            )
        )
