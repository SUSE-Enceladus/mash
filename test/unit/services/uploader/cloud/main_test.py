from pytest import raises
from unittest.mock import patch
from unittest.mock import Mock

from mash.services.uploader.cloud import Upload
from mash.mash_exceptions import MashUploadSetupException


class TestUpload(object):
    @patch('mash.services.uploader.cloud.UploadAmazon')
    @patch('mash.services.uploader.cloud.Conventions')
    def test_upload_amazon(
        self, mock_Conventions, mock_UploadAmazon
    ):
        conventions = Mock()
        credentials = {}
        mock_Conventions.return_value = conventions
        Upload('ec2', 'file', 'name', 'description', credentials)
        conventions.is_valid_name.assert_called_once_with('name')
        mock_UploadAmazon.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description', credentials)

    @patch('mash.services.uploader.cloud.UploadAzure')
    @patch('mash.services.uploader.cloud.Conventions')
    def test_upload_azure(
        self, mock_Conventions, mock_UploadAzure
    ):
        conventions = Mock()
        credentials = {}
        mock_Conventions.return_value = conventions
        Upload('azure', 'file', 'name', 'description', credentials)
        conventions.is_valid_name.assert_called_once_with('name')
        mock_UploadAzure.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description', credentials)

    @patch('mash.services.uploader.cloud.UploadGCE')
    @patch('mash.services.uploader.cloud.Conventions')
    def test_upload_gce(
        self, mock_Conventions, mock_UploadGCE
    ):
        conventions = Mock()
        credentials = {}
        mock_Conventions.return_value = conventions
        Upload('gce', 'file', 'name', 'description', credentials)
        conventions.is_valid_name.assert_called_once_with('name')
        mock_UploadGCE.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
