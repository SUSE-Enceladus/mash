from mash.services.credentials.amazon import CredentialsAmazon


class TestCredentialsAmazon(object):
    def setup(self):
        self.credentials = CredentialsAmazon()

    def test_set_credentials(self):
        self.credentials.set_credentials('token')
        assert self.credentials.secret_token == 'token'

    def test_get_credentials(self):
        assert self.credentials.get_credentials() == {
            'access_key': None,
            'secret_key': None,
            'ssh_key_private_key_file': None,
            'ssh_key_pair_name': None
        }
