from mash.services.test.config import TestConfig


class TestTestConfig(object):
    def setup(self):
        self.empty_config = TestConfig('test/data/empty_mash_config.yaml')
        self.config = TestConfig('test/data/mash_config.yaml')

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('test') == \
            '/var/log/mash/test_service.log'

    def test_get_img_proof_timeout(self):
        assert self.empty_config.get_img_proof_timeout() == 600
