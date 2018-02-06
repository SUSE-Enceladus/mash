from mash.services.credentials.config import CredentialsConfig


class TestCredentialsConfig(object):
    def setup(self):
        self.config = CredentialsConfig(
            '../data/mash_config.yaml'
        )

    def test_config_data(self):
        assert self.config.config_data

    def test_get_log_file(self):
        assert self.config.get_log_file('credentials') == \
            '/var/log/mash/credentials_service.log'
