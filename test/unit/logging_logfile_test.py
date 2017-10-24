from pytest import raises
from mock import call, patch
from mock import Mock

from mash.logging_logfile import MashLog
from mash.exceptions import MashLogSetupError


class TestMashLog(object):
    @patch('logging.FileHandler')
    @patch('logging.Formatter')
    @patch('mash.logging_logfile.RabbitMQHandler')
    def test_set_logfile(
        self, mock_RabbitMQHandler, mock_logging_Formatter,
        mock_logging_FileHandler
    ):
        log = Mock()
        logfile_handler = Mock()
        mock_logging_FileHandler.return_value = logfile_handler

        rabbit_handler = Mock()
        mock_RabbitMQHandler.return_value = rabbit_handler

        MashLog.set_logfile(log, '/some/log')
        mock_logging_FileHandler.assert_called_once_with(
            encoding='utf-8', filename='/some/log'
        )
        mock_logging_Formatter.assert_called_once_with(
            '%(levelname)-6s: %(asctime)-8s | %(message)s', '%H:%M:%S'
        )

        mock_RabbitMQHandler.assert_called_once_with(
            host='localhost',
            routing_key='mash.{level}'
        )
        log.addHandler.assert_has_calls(
            [call(logfile_handler), call(rabbit_handler)]
        )

    @patch('logging.FileHandler')
    def test_set_logfile_raises(self, mock_logging_FileHandler):
        mock_logging_FileHandler.side_effect = Exception
        with raises(MashLogSetupError):
            MashLog.set_logfile(Mock(), '/some/log')
