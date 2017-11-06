from pytest import raises
from mock import patch
from mock import Mock

from mash.services.uploader import Upload
from mash.mash_exceptions import MashUploadSetupException


class TestUpload(object):
    @patch('mash.services.uploader.UploadAmazon')
    @patch('mash.services.uploader.Conventions')
    @patch('mash.services.uploader.Credentials')
    def test_upload_amazon(
        self, mock_Credentials, mock_Conventions, mock_UploadAmazon
    ):
        conventions = Mock()
        mock_Conventions.return_value = conventions
        Upload('ec2', 'file', 'name', 'description')
        conventions.is_valid_name.assert_called_once_with('name')
        mock_UploadAmazon.assert_called_once_with(
            mock_Credentials.return_value, 'file', 'name', 'description', None
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description')
