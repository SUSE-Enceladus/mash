import logging

from mock import Mock, patch

from mash.handlers import RabbitMQHandler, RabbitMQSocket


class TestRabbitMQHandler(object):
    @patch('mash.handlers.pika.BlockingConnection')
    @patch('mash.handlers.pika.ConnectionParameters')
    def setup(self, mock_pika_ConnectionParams, mock_pika_BlockingConnection):
        self.connection = Mock()
        self.channel = Mock()
        self.channel.exchange_declare.return_value = None
        self.channel.basic_publish.return_value = None
        self.connection.channel.return_value = self.channel

        mock_pika_BlockingConnection.return_value = self.connection
        mock_pika_ConnectionParams.return_value = None
        self.handler = RabbitMQHandler()

    def test_rabbit_handler_messages(self):
        log = logging.getLogger('log_handler_test')
        log.addHandler(self.handler)
        log.setLevel(logging.DEBUG)
        log.info('Test %s', 'args')

        try:
            raise Exception('Broken')
        except Exception:
            log.exception('Test exc_info')

    @patch('mash.handlers.pika.BasicProperties')
    @patch('mash.handlers.pika.BlockingConnection')
    @patch('mash.handlers.pika.ConnectionParameters')
    def test_rabbit_socket(self, mock_pika_ConnectionParams,
                           mock_pika_BlockingConnection,
                           mock_pika_BasicProperties):
        self.connection = Mock()
        self.channel = Mock()
        self.channel.exchange_declare.return_value = None
        self.channel.basic_publish.return_value = None
        self.connection.channel.return_value = self.channel
        self.connection.close.return_value = None

        mock_pika_BlockingConnection.return_value = self.connection
        mock_pika_ConnectionParams.return_value = None
        socket = RabbitMQSocket('host', 1234, 'user', 'pass', 'exchange')

        mock_pika_BlockingConnection.assert_called_once_with(None)
        mock_pika_ConnectionParams.assert_called_once_with(
            host='host',
            port=1234
        )

        self.connection.channel.assert_called_once_with()
        self.channel.exchange_declare.assert_called_once_with(
            exchange='exchange',
            type='topic',
            durable=True
        )

        props = Mock()
        mock_pika_BasicProperties.return_value = props

        msg = '{"levelname": "INFO"}'
        socket.sendall(msg)

        self.channel.basic_publish.assert_called_once_with(
            exchange='exchange',
            routing_key='mash.INFO',
            body=msg,
            properties=props
        )

        socket.close()
        self.connection.close.assert_called_once_with()

        self.connection.close.reset_mock()
        self.connection.close.side_effect = Exception('Already closed!')
        socket.close()
        self.connection.close.assert_called_once_with()
