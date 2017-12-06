import logging

from mock import Mock, patch

from mash.log.handler import (
    RabbitMQHandler,
    RabbitMQSocket
)


class TestRabbitMQHandler(object):
    @patch('mash.log.handler.UriConnection')
    def setup(self, mock_uri_connection):
        self.connection = Mock()
        self.channel = Mock()
        self.channel.exchange.declare.return_value = None
        self.channel.basic.publish.return_value = None
        self.connection.channel.return_value = self.channel

        mock_uri_connection.return_value = self.connection
        self.handler = RabbitMQHandler()

    def test_rabbit_handler_messages(self):
        log = logging.getLogger('log_handler_test')
        log.addHandler(self.handler)
        log.setLevel(logging.DEBUG)
        log.info('Test %s', 'args')
        log.info('Job finished!', extra={'job_id': '4711'})

        try:
            raise Exception('Broken')
        except Exception:
            log.exception('Test exc_info')

    @patch('mash.log.handler.UriConnection')
    def test_rabbit_socket(self, mock_uri_connection):
        self.connection = Mock()
        self.channel = Mock()
        self.channel.exchange.declare.return_value = None
        self.channel.basic.publish.return_value = None
        self.connection.channel.return_value = self.channel
        self.connection.close.return_value = None

        mock_uri_connection.return_value = self.connection
        socket = RabbitMQSocket(
            'host',
            1234,
            'user',
            'pass',
            'exchange',
            'mash.logger'
        )

        mock_uri_connection.assert_called_once_with(
            'amqp://guest:guest@host:1234/%2F?heartbeat=600'
        )

        self.connection.channel.assert_called_once_with()
        self.channel.exchange.declare.assert_called_once_with(
            exchange='exchange',
            exchange_type='direct',
            durable=True
        )

        msg = '{"levelname": "INFO"}'
        socket.sendall(msg)

        self.channel.basic.publish.assert_called_once_with(
            exchange='exchange',
            routing_key='mash.logger',
            body=msg,
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            }
        )

        socket.close()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()
