from mash.services.uploader.credentials.amazon import CredentialsAmazon


class TestCredentialsAmazon(object):
    def setup(self):
        self.credentials = CredentialsAmazon()

    def test_get_credentials(self):
        assert self.credentials.get_credentials() == {
            'access_key': None,
            'secret_key': None,
            'ssh_key_private_key_file': None,
            'ssh_key_pair_name': None
        }
