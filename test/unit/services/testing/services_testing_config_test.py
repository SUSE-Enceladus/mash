from mash.services.testing.config import TestingConfig


class TestTestingConfig(object):
    def setup(self):
        self.empty_config = TestingConfig('../data/empty_testing_config.yml')

    def test_config_data(self):
        assert self.empty_config.config_data
