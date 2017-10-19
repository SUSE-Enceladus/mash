from pytest import raises
from mock import patch

from mash.services.uploader.credentials import Credentials
from mash.exceptions import MashCredentialsError


class TestCredentials(object):
    @patch('mash.services.uploader.credentials.CredentialsAmazon')
    def test_credentials_amazon(self, mock_CredentialsAmazon):
        Credentials('ec2')
        mock_CredentialsAmazon.assert_called_once_with(None)
        with raises(MashCredentialsError):
            Credentials('foo')
