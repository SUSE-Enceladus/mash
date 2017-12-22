import logging

from unittest.mock import Mock, patch

from mash.log.handler import (
    RabbitMQHandler,
    RabbitMQSocket
)


class TestRabbitMQHandler(object):
    def setup(self):
        self.connection = Mock()
        self.channel = Mock()
        self.channel.exchange.declare.return_value = None
        self.channel.basic.publish.return_value = None
        self.connection.channel.return_value = self.channel

        self.handler = RabbitMQHandler()

    @patch('mash.log.handler.Connection')
    def test_rabbit_handler_messages(self, mock_connection):
        mock_connection.return_value = self.connection

        log = logging.getLogger('log_handler_test')
        log.addHandler(self.handler)
        log.setLevel(logging.DEBUG)

        log.info('Test %s', 'args')
        self.channel.basic.publish.assert_called_once_with(
            exchange='logger',
            routing_key='mash.logger',
            body='{"msg": "Test args"}',
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            }
        )
        self.channel.basic.publish.reset_mock()

        log.info('Job finished!', extra={'job_id': '4711'})
        self.channel.basic.publish.assert_called_once_with(
            exchange='logger',
            routing_key='mash.logger',
            body='{"job_id": "4711", "msg": "Job finished!"}',
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            }
        )
        self.channel.basic.publish.reset_mock()

        try:
            raise Exception('Broken')
        except Exception:
            log.exception('Test exc_info')

        assert self.channel.basic.publish.call_count == 1

    @patch('mash.log.handler.Connection')
    def test_rabbit_socket(self, mock_connection):
        mock_connection.return_value = self.connection
        self.connection.close.return_value = None

        socket = RabbitMQSocket(
            'host',
            1234,
            'user',
            'pass',
            'exchange',
            'mash.logger'
        )

        mock_connection.assert_called_once_with(
            'host',
            'user',
            'pass',
            port=1234,
            kwargs={'heartbeat': 600}
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
