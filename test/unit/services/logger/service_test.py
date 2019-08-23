import io
import json
import sys

from unittest.mock import MagicMock, Mock, patch
from pytest import raises

from mash.mash_exceptions import MashLoggerException
from mash.services.mash_service import MashService
from mash.services.logger.service import LoggerService

open_name = "__builtin__.open" if sys.version_info.major < 3 \
    else "builtins.open"


class TestLoggerService(object):

    @patch.object(MashService, '__init__')
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
        self.logger.log = MagicMock()
        self.logger.service_exchange = 'logger'
        self.logger.channel = self.channel

    @patch('mash.services.logger.service.setup_logfile')
    @patch.object(LoggerService, 'start')
    @patch.object(LoggerService, 'bind_queue')
    @patch.object(LoggerService, '_process_log')
    def test_logger_post_init(
        self, mock_process_log, mock_bind_queue, mock_start, mock_setup_logfile
    ):
        config = Mock()
        config.get_log_file.return_value = '/var/log/mash/logger_service.log'
        self.logger.config = config

        # Test normal run
        self.logger.post_init()

        config.get_log_file.assert_called_once_with('logger')
        mock_setup_logfile.assert_called_once_with(
            '/var/log/mash/logger_service.log'
        )
        mock_bind_queue.assert_called_once_with(
            'logger', 'mash.logger', 'logging'
        )
        mock_start.assert_called_once_with()

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

    @patch.object(LoggerService, 'consume_queue')
    @patch.object(LoggerService, 'close_connection')
    def test_logger_start(self, mock_close_connection, mock_consume_queue):
        self.logger.channel = self.channel
        self.logger.start()
        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_called_once_with(
            self.logger._process_log, 'logging'
        )
        mock_close_connection.assert_called_once_with()

    @patch.object(LoggerService, 'consume_queue')
    @patch.object(LoggerService, 'close_connection')
    def test_logger_start_exception(
        self, mock_close_connection, mock_consume_queue
    ):
        scheduler = Mock()
        self.logger.scheduler = scheduler
        self.logger.channel = self.channel

        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.logger.start()

        mock_close_connection.assert_called_once_with()
        mock_close_connection.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start scheduler.'
        )

        with raises(Exception) as error:
            self.logger.start()

        assert 'Cannot start scheduler.' == str(error.value)
