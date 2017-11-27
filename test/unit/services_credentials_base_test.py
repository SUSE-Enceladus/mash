from mash.services.credentials.base import CredentialsBase

import jwt


class TestCredentialsBase(object):
    def setup(self):
        self.credentials = CredentialsBase()

    def test_set_credentials(self):
        token = jwt.encode(
            {'some': 'payload'}, 'secret', algorithm='HS256'
        )
        self.credentials.set_credentials(token)
        assert self.credentials.credentials['some'] == 'payload'

    def test_get_credentials(self):
        assert self.credentials.get_credentials() == {}
