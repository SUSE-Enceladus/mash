from mash.services.logger.config import LoggerConfig


class TestLoggerConfig(object):
    def setup(self):
        self.empty_config = LoggerConfig('../data/empty_mash_config.yaml')

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('logger') == \
            '/var/log/mash/logger_service.log'
