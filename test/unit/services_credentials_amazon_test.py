from mash.services.credentials.amazon import CredentialsAmazon


class TestCredentialsAmazon(object):
    def setup(self):
        self.credentials = CredentialsAmazon()

    def test_post_init(self):
        assert self.credentials.get_credentials() == {
            'access_key': None,
            'secret_key': None,
            'ssh_key_private_key_file': None,
            'ssh_key_pair_name': None
        }
