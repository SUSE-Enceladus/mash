from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock
from pytest import raises

from mash.services.base_service import BaseService

from mash.mash_exceptions import (
    MashRabbitConnectionException,
    MashLogSetupException
)


class TestBaseService(object):
    @patch('mash.services.base_service.Connection')
    def setup(self, mock_connection):
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
        self.service = BaseService('localhost', 'obs')
        self.service.log = Mock()
        mock_connection.side_effect = Exception
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

    @patch('mash.services.base_service.Connection')
    def test_publish_job_result(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_job_result('exchange', 'job_id', 'message')
        self.channel.queue.declare.assert_called_once_with(
            queue='exchange.service', durable=True
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='exchange', routing_key='job_id',
            queue='exchange.service'
        )
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='exchange', mandatory=True,
            properties=self.msg_properties, routing_key='job_id'
        )

    @patch('mash.services.base_service.Connection')
    def test_publish_credentials_result(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_credentials_result('job_id', 'csp', 'message')
        self.channel.queue.declare.assert_called_once_with(
            queue='credentials.csp', durable=True
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='credentials', routing_key='job_id',
            queue='credentials.csp'
        )
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='credentials', mandatory=True,
            properties=self.msg_properties, routing_key='job_id'
        )

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback, 'service')
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='obs.service'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()
