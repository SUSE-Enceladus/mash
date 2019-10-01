from mash.services.replication.config import ReplicationConfig


class TestReplicationConfig(object):
    def setup(self):
        self.config = ReplicationConfig(
            'test/data/mash_config.yaml'
        )

    def test_config_data(self):
        assert self.config.config_data

    def test_get_log_file(self):
        assert self.config.get_log_file('replication') == \
            '/tmp/log/replication_service.log'
