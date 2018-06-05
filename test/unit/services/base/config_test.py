from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig
from pytest import raises


class TestBaseConfig(object):
    def setup(self):
        self.empty_config = BaseConfig('../data/empty_mash_config.yaml')
        self.config = BaseConfig('../data/mash_config.yaml')

    def test_get_encryption_keys_file(self):
        enc_keys_file = self.empty_config.get_encryption_keys_file()
        assert enc_keys_file == '/var/lib/mash/encryption_keys'

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

    def test_get_provider_data(self):
        data = self.config.get_provider_data()
        assert data['ec2']['regions']['aws-cn'] == ['cn-north-1']
        assert data['ec2']['helper_images']['cn-north-1'] == 'ami-bcc45885'

        with raises(MashConfigException) as error:
            self.empty_config.get_provider_data()

        assert str(error.value) == \
            'Provider data must be provided in config file.'

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

    def test_get_ssh_private_key_file(self):
        assert self.config.get_ssh_private_key_file() == \
            '/var/lib/mash/ssh_key'

        with raises(MashConfigException) as error:
            self.empty_config.get_ssh_private_key_file()

        assert str(error.value) == \
            'ssh_private_key_file is required in MASH configuration file.'
