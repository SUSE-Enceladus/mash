from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig
from pytest import raises


class TestBaseConfig(object):
    def setup(self):
        self.empty_config = BaseConfig('../data/empty_mash_config.yaml')
        self.config = BaseConfig('../data/mash_config.yaml')

    def test_get_jwt_algorithm(self):
        algorithm = self.empty_config.get_jwt_algorithm()
        assert algorithm == 'HS256'

    def test_get_jwt_secret(self):
        secret = self.config.get_jwt_secret()
        assert secret == 'abc123'

    def test_get_jwt_secret_empty(self):
        msg = 'jwt_secret must be in config file.'
        with raises(MashConfigException) as error:
            self.empty_config.get_jwt_secret()

        assert msg == str(error.value)

    def test_get_private_key_file(self):
        assert self.config.get_private_key_file() == '/etc/mash/creds_key'

    def test_get_services_names(self):
        # Services requiring credentials
        expected = [
            'uploader', 'testing', 'replication', 'publisher',
            'deprecation', 'pint'
        ]
        services = self.empty_config.get_service_names(
            credentials_required=True
        )
        assert expected == services

        # All services
        expected = ['obs'] + expected
        services = self.empty_config.get_service_names()
        assert expected == services
