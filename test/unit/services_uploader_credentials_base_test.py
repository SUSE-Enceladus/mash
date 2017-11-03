from pytest import raises

from mash.services.uploader.credentials.base import CredentialsBase


class TestCredentialsBase(object):
    def setup(self):
        self.credentials = CredentialsBase()

    def test_get_credentials(self):
        with raises(NotImplementedError):
            self.credentials.get_credentials()
