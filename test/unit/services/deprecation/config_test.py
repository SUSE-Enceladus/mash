from mash.services.deprecation.config import DeprecationConfig


class TestDeprecationConfig(object):
    def setup(self):
        self.empty_config = DeprecationConfig('test/data/empty_mash_config.yaml')

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('deprecation') == \
            '/var/log/mash/deprecation_service.log'
