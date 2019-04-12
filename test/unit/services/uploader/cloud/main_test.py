from pytest import raises
from unittest.mock import patch

from mash.services.uploader.cloud import Upload
from mash.mash_exceptions import MashUploadSetupException


class TestUpload(object):
    @patch('mash.services.uploader.cloud.UploadAmazon')
    def test_upload_amazon(
        self, mock_UploadAmazon
    ):
        credentials = {}
        Upload('ec2', 'file', 'name', 'description', credentials)
        mock_UploadAmazon.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description', credentials)

    @patch('mash.services.uploader.cloud.UploadAzure')
    def test_upload_azure(
        self, mock_UploadAzure
    ):
        credentials = {}
        Upload('azure', 'file', 'name', 'description', credentials)
        mock_UploadAzure.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
        with raises(MashUploadSetupException):
            Upload('foo', 'file', 'name', 'description', credentials)

    @patch('mash.services.uploader.cloud.UploadGCE')
    def test_upload_gce(
        self, mock_UploadGCE
    ):
        credentials = {}
        Upload('gce', 'file', 'name', 'description', credentials)
        mock_UploadGCE.assert_called_once_with(
            credentials, 'file', 'name', 'description', None, 'x86_64'
        )
