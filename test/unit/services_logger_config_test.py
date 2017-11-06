from mock import patch
from pytest import raises

from mash.mash_exceptions import MashLoggerException
from mash.services.logger.config import LoggerConfig


class TestLoggerConfig(object):
    def setup(self):
        self.config = LoggerConfig('../data/logger_config.yml')
        self.empty_config = LoggerConfig('../data/empty_logger_config.yml')

    @patch('os.path.exists')
    def test_get_log_dir(self, mock_os):
        mock_os.return_value = True
        assert self.config.get_log_dir() == '/var/log/othermash/'
        assert self.empty_config.get_log_dir() == '/var/log/mash/'

    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_make_dirs_exception(self, mock_os_path, mock_os_makedirs):
        mock_os_path.return_value = False
        mock_os_makedirs.side_effect = Exception('Cannot make dir.')

        with raises(MashLoggerException):
            self.config.get_log_dir()

    @patch.object(LoggerConfig, 'get_log_dir')
    def test_get_log_file(self, mock_get_log_dir):
        mock_get_log_dir.return_value = '/var/log/mash/'
        assert self.empty_config.get_log_file('1234') == \
            '/var/log/mash/1234.log'
