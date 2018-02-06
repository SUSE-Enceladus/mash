from pytest import raises
from unittest.mock import patch

from mash.services.credentials import Credentials
from mash.mash_exceptions import MashCredentialsException


class TestCredentials(object):
    @patch('mash.services.credentials.CredentialsAmazon')
    def test_credentials_amazon(self, mock_CredentialsAmazon):
        Credentials('ec2')
        mock_CredentialsAmazon.assert_called_once_with()
        with raises(MashCredentialsException):
            Credentials('foo')
