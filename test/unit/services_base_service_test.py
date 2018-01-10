import io

from unittest.mock import patch
from unittest.mock import call
from unittest.mock import MagicMock, Mock
from pytest import raises

from mash.services.base_service import BaseService
from mash.services.base_defaults import Defaults

from mash.mash_exceptions import (
    MashRabbitConnectionException,
    MashLogSetupException
)

open_name = "builtins.open"


class TestBaseService(object):
    @patch.object(Defaults, 'get_job_directory')
    @patch('mash.services.base_service.Connection')
    def setup(self, mock_connection, mock_get_job_directory):
        mock_get_job_directory.return_value = '/var/lib/mash/obs_jobs/'
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
        mock_get_job_directory.assert_called_once_with('obs')
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
    def test_publish_service_message(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_service_message('message')
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='obs', mandatory=True,
            properties=self.msg_properties, routing_key='service_event'
        )

    @patch('mash.services.base_service.Connection')
    def test_publish_listener_message(self, mock_connection):
        mock_connection.return_value = self.connection
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

    @patch('mash.services.base_service.NamedTemporaryFile')
    def test_persist_job_config(self, mock_temp_file):
        self.service.job_directory = 'tmp-dir'

        tmp_file = Mock()
        tmp_file.name = 'tmp-dir/job-test.json'
        mock_temp_file.return_value = tmp_file

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service.persist_job_config({'id': '1'})
            file_handle = mock_open.return_value.__enter__.return_value
            # Dict is mutable, mock compares the final value of Dict
            # not the initial value that was passed in.
            file_handle.write.assert_called_with(
                u'{"id": "1", "job_file": "tmp-dir/job-test.json"}'
            )

    @patch('mash.services.base_service.json.load')
    @patch('mash.services.base_service.os.listdir')
    def test_restart_jobs(self, mock_os_listdir, mock_json_load):
        self.service.job_directory = 'tmp-dir'
        mock_os_listdir.return_value = ['job-123.json']
        mock_json_load.return_value = {'id': '1'}

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            mock_callback = Mock()
            self.service.restart_jobs(mock_callback)

            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.call_count == 1

        mock_callback.assert_called_once_with({'id': '1'})
