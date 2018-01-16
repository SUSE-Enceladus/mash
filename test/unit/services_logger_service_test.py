import io
import json
import sys

from amqpstorm import AMQPError

from unittest.mock import MagicMock, Mock, patch
from pytest import raises

from mash.mash_exceptions import MashLoggerException
from mash.services.base_service import BaseService
from mash.services.logger.config import LoggerConfig
from mash.services.logger.service import LoggerService

open_name = "__builtin__.open" if sys.version_info.major < 3 \
    else "builtins.open"


class TestLoggerService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.get_log_file.return_value = '/tmp/file.log'

        self.channel = Mock()
        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        body = {
            "levelname": "INFO",
            "msg": u"INFO 2017-11-01 11:36:36.782072 "
                   "LoggerService \n Job[4711]: Test log message! \n",
            "job_id": "4711"
        }
        self.message = MagicMock(
            body=json.dumps(body),
            channel=self.channel,
            method=self.method
        )

        self.logger = LoggerService()
        self.logger.service_exchange = 'logger'
        self.logger.channel = self.channel

    @patch.object(LoggerService, 'stop')
    @patch.object(LoggerService, 'start')
    @patch.object(LoggerConfig, '__init__')
    @patch.object(LoggerService, '_bind_queue')
    @patch.object(LoggerService, '_process_log')
    @patch.object(LoggerService, 'consume_queue')
    def test_logger_post_init(
        self, mock_consume_queue, mock_process_log,
        mock_bind_queue, mock_logger_config, mock_start, mock_stop
    ):
        mock_logger_config.return_value = None

        # Test normal run
        self.logger.post_init()

        mock_consume_queue.assert_called_once_with(
            mock_process_log, 'logging'
        )
        mock_bind_queue.assert_called_once_with(
            'logger', 'mash.logger', 'logging'
        )
        mock_start.assert_called_once_with()
        mock_stop.assert_called_once_with()

        # Test keyboard interrupt
        mock_start.side_effect = KeyboardInterrupt
        mock_stop.reset_mock()

        self.logger.post_init()
        mock_stop.assert_called_once_with()

        # Test unandled exception
        mock_start.side_effect = Exception('Unable to connect.')

        with raises(Exception) as e:
            self.logger.post_init()

        assert 'Unable to connect.' == str(e.value)

    def test_logger_process_invalid_log(self):
        self.message.body = ''
        with raises(MashLoggerException):
            self.logger._process_log(self.message)

    @patch('os.path.exists')
    def test_logger_process_append(
        self, mock_path_exists
    ):
        mock_path_exists.return_value = True
        self.logger.config = self.config

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.logger._process_log(self.message)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_with(
                u'INFO 2017-11-01 11:36:36.782072 '
                'LoggerService \n Test log message! \n'
            )

    @patch('os.path.exists')
    def test_logger_process_write_exception(
        self, mock_path_exists
    ):
        mock_path_exists.return_value = True
        self.logger.config = self.config

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.side_effect = Exception('Error writing file!')

            with raises(MashLoggerException):
                self.logger._process_log(self.message)

    def test_logger_start(self):
        self.channel.consumer_tags = []
        self.logger.channel = self.channel

        self.logger.start()
        self.channel.start_consuming.assert_called_once_with()

    @patch.object(LoggerService, '_open_connection')
    def test_logger_start_exception(self, mock_open_connection):
        self.channel.start_consuming.side_effect = [AMQPError('Broken!'), None]
        self.channel.consumer_tags = []
        self.logger.channel = self.channel

        self.logger.start()
        mock_open_connection.assert_called_once_with()

    @patch.object(LoggerService, 'close_connection')
    def test_logger_stop(self, mock_close_connection):
        self.logger.channel = self.channel

        self.logger.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
