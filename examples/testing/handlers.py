import json
import pika

from logging.handlers import SocketHandler


class RabbitMQHandler(SocketHandler):
    def __init__(self,
                 host='localhost',
                 port='5672',
                 exchange='logger',
                 username='guest',
                 password='guest'):
        super(RabbitMQHandler, self).__init__(host, port)

        self.username = username
        self.password = password
        self.exchange = exchange

    def makeSocket(self):
        return RabbitMQSocket(
            self.host,
            self.port,
            self.username,
            self.password,
            self.exchange
        )

    def makePickle(self, record):
        data = record.__dict__.copy()

        if 'args' in data and data['args']:
            data['msg'] = data['msg'] % data['args']

        if 'exc_info' in data and data['exc_info']:
            data['exc_info'] = self.formatException(data['exc_info'])

        return json.dumps(data)


class RabbitMQSocket(object):
    def __init__(self,
                 host,
                 port,
                 username,
                 password,
                 exchange):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.exchange = exchange
        self.connection = None
        self.channel = None
        self.open()

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass

    def open(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port
            )
        )
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange=self.exchange,
            type='topic',
            durable=True
        )

    def sendall(self, msg):
        level = json.loads(msg)['levelname']
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key='mash.{}'.format(level),
            body=msg,
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2
            )
        )
