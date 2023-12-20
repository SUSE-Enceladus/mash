from unittest.mock import patch
from unittest.mock import Mock
from pytest import raises

from mash.services.mash_service import MashService

from mash.mash_exceptions import MashRabbitConnectionException


class TestBaseService(object):

    @patch('mash.services.mash_service.Connection')
    def setup_method(self, method, mock_connection):
        self.connection = Mock()
        self.channel = Mock()
        self.msg_properties = {
            'content_type': 'application/json',
            'delivery_mode': 2
        }
        queue = Mock()
        queue.method.queue = 'queue'
        self.channel.queue.declare.return_value = queue
        self.channel.exchange.declare.return_value = queue

        self.connection.channel.return_value = self.channel
        self.connection.is_closed = True
        mock_connection.return_value = self.connection

        config = Mock()
        config.get_service_names.return_value = [
            'download', 'upload', 'create', 'raw_image_upload', 'test',
            'replicate', 'publish', 'deprecate'
        ]

        self.service = MashService('download', config=config)

        self.service.log = Mock()
        mock_connection.side_effect = Exception
        with raises(MashRabbitConnectionException):
            MashService('download', config=config)
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback, 'service', 'download')
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='download.service'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()

    def test_unbind_queue(self):
        self.service.unbind_queue(
            'service', 'test', '1'
        )
        self.service.channel.queue.unbind.assert_called_once_with(
            queue='test.service', exchange='test', routing_key='1'
        )
