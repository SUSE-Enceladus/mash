from unittest.mock import patch

from mash.services.testing.config import TestingConfig


class TestTestingConfig(object):
    def setup(self):
        self.empty_config = TestingConfig('../data/empty_testing_config.yml')

    def test_config_data(self):
        assert self.empty_config.config_data

    def test_get_log_file(self):
        assert self.empty_config.get_log_file() == \
            '/var/log/mash/testing_service.log'

    @patch('mash.services.testing.defaults.os.makedirs')
    def test_get_jobs_dir(self, mock_makedirs):
        assert self.empty_config.get_jobs_dir() == \
            '/var/lib/mash/testing_jobs/'
        mock_makedirs.assert_called_once_with(
            '/var/lib/mash/testing_jobs/',
            exist_ok=True
        )
