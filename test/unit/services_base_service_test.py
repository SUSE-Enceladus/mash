from mock import patch
from mock import Mock
from pytest import raises

from mash.exceptions import MashPikaConnectionError
from mash.services.base_service import BaseService


class TestBaseService(object):
    @patch('mash.services.base_service.pika.BlockingConnection')
    def setup(self, mock_pika_BlockingConnection):
        self.connection = Mock()
        self.channel = Mock()
        queue = Mock()
        queue.method.queue = 'queue'
        self.channel.queue_declare.return_value = queue
        self.channel.exchange_declare.return_value = queue
        self.connection.channel.return_value = self.channel
        self.connection.is_closed = True
        mock_pika_BlockingConnection.return_value = self.connection
        self.service = BaseService('localhost', 'obs')
        self.basic_properties = Mock()
        self.service.pika_properties = self.basic_properties
        mock_pika_BlockingConnection.side_effect = Exception
        with raises(MashPikaConnectionError):
            BaseService('localhost', 'obs')
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    def test_publish_service_message(self):
        self.service.publish_service_message('message')
        self.channel.basic_publish.assert_called_once_with(
            body='message', exchange='obs', mandatory=True,
            properties=self.basic_properties, routing_key='service_event'
        )

    def test_publish_listener_message(self):
        self.service.publish_listener_message('id', 'message')
        self.channel.basic_publish.assert_called_once_with(
            body='message', exchange='obs', mandatory=True,
            properties=self.basic_properties, routing_key='listener_id'
        )

    def test_bind_service_queue(self):
        assert self.service.bind_service_queue() == 'queue'
        self.channel.exchange_declare.assert_called_once_with(
            durable=True, exchange='obs', exchange_type='topic'
        )
        self.channel.queue_bind.assert_called_once_with(
            exchange='obs', queue='queue', routing_key='service_event'
        )

    def test_bind_listener_queue(self):
        self.service.bind_listener_queue('id')
        self.channel.queue_bind.assert_called_once_with(
            exchange='obs', queue='queue', routing_key='listener_id'
        )

    def test_delete_listener_queue(self):
        self.service.delete_listener_queue('id')
        self.channel.queue_delete.assert_called_once_with(
            queue='obs.listener_id'
        )

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback, 'queue')
        self.channel.basic_consume.assert_called_once_with(
            callback, queue='queue'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()

        self.connection.close.reset_mock()
        self.connection.close.side_effect = Exception('Error!')
        self.service.close_connection()
        assert self.connection.close.call_count == 0
