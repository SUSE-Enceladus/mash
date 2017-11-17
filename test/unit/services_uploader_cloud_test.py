from pytest import raises
from mock import patch
from mock import Mock

from mash.services.uploader.cloud import Upload
from mash.mash_exceptions import MashUploadSetupException


class TestUpload(object):
    @patch('mash.services.uploader.cloud.UploadAmazon')
    @patch('mash.services.uploader.cloud.Conventions')
    @patch('mash.services.uploader.cloud.Credentials')
    def test_upload_amazon(
        self, mock_Credentials, mock_Conventions, mock_UploadAmazon
    ):
        conventions = Mock()
        credentials = Mock()
        mock_Conventions.return_value = conventions
        mock_Credentials.return_value = credentials
        Upload('ec2', 'file', 'name', 'description', 'credentials_token')
        conventions.is_valid_name.assert_called_once_with('name')
        credentials.set_credentials.assert_called_once_with(
            'credentials_token'
        )
        mock_UploadAmazon.assert_called_once_with(
            mock_Credentials.return_value, 'file', 'name', 'description', None
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description', 'credentials_token')
