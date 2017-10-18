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
        mock_pika_BlockingConnection.side_effect = Exception
        with raises(MashPikaConnectionError):
            BaseService('localhost', 'obs')
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    def test_publish_service_message(self):
        self.service.publish_service_message('message')
        self.connection.connect.assert_called_once_with()
        self.channel.open.assert_called_once_with()
        self.channel.basic_publish.assert_called_once_with(
            body='message', exchange='obs', routing_key='service_event'
        )

    def test_publish_listener_message(self):
        self.service.publish_listener_message('id', 'message')
        self.channel.basic_publish.assert_called_once_with(
            body='message', exchange='obs', routing_key='listener_id'
        )

    def test_publish_log_message(self):
        self.service.publish_log_message('message')
        self.channel.basic_publish.assert_called_once_with(
            body='message', exchange='logger', routing_key='log_event'
        )

    def test_bind_service_queue(self):
        assert self.service.bind_service_queue() == 'queue'
        self.channel.exchange_declare.assert_called_once_with(
            exchange='obs', exchange_type='direct'
        )
        self.channel.queue_bind.assert_called_once_with(
            exchange='obs', queue='queue', routing_key='service_event'
        )

    def test_bind_log_queue(self):
        self.service.bind_log_queue()
        self.channel.queue_bind.assert_called_once_with(
            exchange='logger', queue='queue', routing_key='log_event'
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
            callback, no_ack=True, queue='queue'
        )
