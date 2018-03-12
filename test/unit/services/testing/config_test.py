from pytest import raises

from mash.mash_exceptions import MashConfigException
from mash.services.testing.config import TestingConfig


class TestTestingConfig(object):
    def setup(self):
        self.empty_config = TestingConfig('../data/empty_mash_config.yaml')
        self.config = TestingConfig('../data/mash_config.yaml')

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('testing') == \
            '/var/log/mash/testing_service.log'

    def test_get_ssh_private_key_file(self):
        assert self.config.get_ssh_private_key_file() == \
            '/etc/mash/testing_key'

        with raises(MashConfigException) as error:
            self.empty_config.get_ssh_private_key_file()

        assert str(error.value)
