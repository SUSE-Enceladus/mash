from mash.services.publisher.config import PublisherConfig


class TestPublisherConfig(object):
    def setup(self):
        self.config = PublisherConfig(
            '../data/mash_config.yaml'
        )

    def test_publisher_config_data(self):
        assert self.config.config_data

    def test_publisher_get_log_file(self):
        assert self.config.get_log_file('publisher') == \
            '/var/log/mash/publisher_service.log'
