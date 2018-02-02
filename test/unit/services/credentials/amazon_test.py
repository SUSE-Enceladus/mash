from mash.services.credentials.amazon import CredentialsAmazon


class TestCredentialsAmazon(object):
    def setup(self):
        self.credentials = CredentialsAmazon(custom_args={
            'access_key_id': '123456',
            'secret_access_key': '654321',
            'ssh_key_name': 'key-one',
            'ssh_private_key': 'key-file.pem'
        })

    def test_post_init(self):
        assert self.credentials.get_credentials() == {
            'access_key_id': '123456',
            'secret_access_key': '654321',
            'ssh_key_name': 'key-one',
            'ssh_private_key': 'key-file.pem'
        }
