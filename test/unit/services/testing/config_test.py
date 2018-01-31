from mash.services.testing.config import TestingConfig


class TestTestingConfig(object):
    def setup(self):
        self.empty_config = TestingConfig('../data/empty_testing_config.yml')

    def test_config_data(self):
        assert self.empty_config.config_data

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('testing') == \
            '/var/log/mash/testing_service.log'
