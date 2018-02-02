from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig
from pytest import raises


class TestBaseConfig(object):
    def setup(self):
        self.empty_config = BaseConfig('../data/empty_mash_config.yaml')
        self.config = BaseConfig('../data/mash_config.yaml')

    def test_get_jwt_secret(self):
        secret = self.config.get_jwt_secret()
        assert secret == 'abc123'

    def test_get_jwt_secret_empty(self):
        msg = 'jwt_secret must be in config file.'
        with raises(MashConfigException) as error:
            self.empty_config.get_jwt_secret()

        assert msg == str(error.value)
