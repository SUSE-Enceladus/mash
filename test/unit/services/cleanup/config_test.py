from mash.services.cleanup.config import CleanupConfig


class TestTestConfig(object):
    def setup_method(self):
        self.empty_config = CleanupConfig('test/data/empty_mash_config.yaml')
        self.config = CleanupConfig('test/data/mash_config.yaml')

    def test_get_max_image_age(self):
        assert self.empty_config.get_max_image_age() == 90
