from mash.services.credentials.base import CredentialsBase


class TestCredentialsBase(object):
    def setup(self):
        self.credentials = CredentialsBase()

    def test_set_credentials(self):
        self.credentials.set_credentials()
