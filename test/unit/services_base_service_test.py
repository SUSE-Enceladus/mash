from mock import patch
from mock import call
from mock import Mock
from pytest import raises

from mash.services.base_service import BaseService

from mash.mash_exceptions import (
    MashRabbitConnectionException,
    MashLogSetupException
)


class TestBaseService(object):
    @patch('mash.services.base_service.UriConnection')
    def setup(self, mock_uri_onnection):
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
        mock_uri_onnection.return_value = self.connection
        self.service = BaseService('localhost', 'obs')
        self.service.log = Mock()
        mock_uri_onnection.side_effect = Exception
        with raises(MashRabbitConnectionException):
            BaseService('localhost', 'obs')
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    @patch('logging.FileHandler')
    def test_set_logfile(self, mock_logging_FileHandler):
        logfile_handler = Mock()
        mock_logging_FileHandler.return_value = logfile_handler

        self.service.set_logfile('/some/log')
        mock_logging_FileHandler.assert_called_once_with(
            encoding='utf-8', filename='/some/log'
        )
        self.service.log.addHandler.assert_has_calls(
            [call(logfile_handler)]
        )

    @patch('logging.FileHandler')
    def test_set_logfile_raises(self, mock_logging_FileHandler):
        mock_logging_FileHandler.side_effect = Exception
        with raises(MashLogSetupException):
            self.service.set_logfile('/some/log')

    @patch('mash.services.base_service.UriConnection')
    def test_publish_service_message(self, mock_uri_connection):
        mock_uri_connection.return_value = self.connection
        self.service.publish_service_message('message')
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='obs', mandatory=True,
            properties=self.msg_properties, routing_key='service_event'
        )

    @patch('mash.services.base_service.UriConnection')
    def test_publish_listener_message(self, mock_uri_connection):
        mock_uri_connection.return_value = self.connection
        self.service.publish_listener_message('id', 'message')
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='obs', mandatory=True,
            properties=self.msg_properties, routing_key='listener_id'
        )

    def test_bind_service_queue(self):
        assert self.service.bind_service_queue() == 'obs.service_event'
        self.channel.exchange.declare.assert_called_once_with(
            durable=True, exchange='obs', exchange_type='direct'
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='obs',
            queue='obs.service_event',
            routing_key='service_event'
        )

    def test_bind_listener_queue(self):
        self.service.bind_listener_queue('id')
        self.channel.queue.bind.assert_called_once_with(
            exchange='obs', queue='obs.listener_id', routing_key='listener_id'
        )

    def test_delete_listener_queue(self):
        self.service.delete_listener_queue('id')
        self.channel.queue.delete.assert_called_once_with(
            queue='obs.listener_id'
        )

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback, 'queue')
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='queue'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()
