from pytest import raises
from mock import patch
from mock import Mock

from mash.logging_logfile import MashLog
from mash.exceptions import MashLogSetupError


class TestMashLog(object):
    @patch('logging.FileHandler')
    @patch('logging.Formatter')
    def test_set_logfile(
        self, mock_logging_Formatter, mock_logging_FileHandler
    ):
        log = Mock()
        logfile_handler = Mock()
        mock_logging_FileHandler.return_value = logfile_handler
        MashLog.set_logfile(log, '/some/log')
        mock_logging_FileHandler.assert_called_once_with(
            encoding='utf-8', filename='/some/log'
        )
        mock_logging_Formatter.assert_called_once_with(
            '%(levelname)-6s: %(asctime)-8s | %(message)s', '%H:%M:%S'
        )
        log.addHandler.assert_called_once_with(logfile_handler)

    @patch('logging.FileHandler')
    def test_set_logfile_raises(self, mock_logging_FileHandler):
        mock_logging_FileHandler.side_effect = Exception
        with raises(MashLogSetupError):
            MashLog.set_logfile(Mock(), '/some/log')
