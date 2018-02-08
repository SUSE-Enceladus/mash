from mash.services.credentials.amazon import CredentialsAmazon


class TestCredentialsAmazon(object):
    def setup(self):
        self.credentials = CredentialsAmazon()
        self.credentials.set_credentials(
            '123456', '654321', 'key-one', 'key-file.pem'
        )

    def test_post_init(self):
        assert self.credentials.access_key_id == '123456'
        assert self.credentials.secret_access_key == '654321'
        assert self.credentials.ssh_key_name == 'key-one'
        assert self.credentials.ssh_private_key == 'key-file.pem'
