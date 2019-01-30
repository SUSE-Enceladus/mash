import io
from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.uploader.cloud.gce import UploadGCE
from mash.mash_exceptions import MashUploadException
from mash.utils.json_format import JsonFormat
from mash.services.uploader.config import UploaderConfig


class TestUploadGCE(object):
    @patch('mash.services.uploader.cloud.gce.NamedTemporaryFile')
    @patch('mash.services.uploader.cloud.gce.get_configuration')
    def setup(self, mock_get_configuration, mock_NamedTemporaryFile):
        tempfile = Mock()
        tempfile.name = 'tempfile'
        mock_NamedTemporaryFile.return_value = tempfile
        self.credentials = Mock()
        self.credentials = {
            'type': 'type',
            'project_id': 'projectid',
            'private_key_id': 'keyid',
            'private_key': 'key',
            'client_email': 'b@email.com',
            'client_id': 'a',
            'auth_uri':
                'https://accounts.google.com/o/oauth2/auth',
            'token_uri':
                'https://accounts.google.com/o/oauth2/token',
            'auth_provider_x509_cert_url':
                'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url':
                'https://www.googleapis.com/robot/v1/metadata/x509/'
        }
        custom_args = {
            'bucket': 'images',
            'family': 'sles-12',
            'region': 'region'
        }
        mock_get_configuration.return_value = UploaderConfig(
            config_file='../data/mash_config.yaml'
        )
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            self.uploader = UploadGCE(
                self.credentials, '/tmp/file.vhdfixed.tar.gz',
                'sles-12-sp4-v20180909', 'description {date}', custom_args,
                'x86_64'
            )
            file_handle.write.assert_called_once_with(
                JsonFormat.json_message(self.credentials)
            )

    @patch('mash.services.uploader.cloud.gce.NamedTemporaryFile')
    def test_init_incomplete_arguments(self, mock_NamedTemporaryFile):
        custom_args = {
            'bucket': 'images',
            'family': 'sles-12',
            'region': 'region'
        }
        with patch('builtins.open', create=True):
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'sles-11-sp4', 'description {date}', custom_args, 'x86_64'
                )
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'name', 'description', custom_args, 'x86_64'
                )
            del custom_args['region']
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'name', 'description  {date}', custom_args, 'x86_64'
                )
            del custom_args['family']
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'name', 'description  {date}', custom_args, 'x86_64'
                )
            del custom_args['bucket']
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'name', 'description  {date}', custom_args, 'x86_64'
                )
            with raises(MashUploadException):
                UploadGCE(
                    self.credentials, 'file.vhdfixed.tar.gz',
                    'name', 'description {date}', None, 'x86_64'
                )

    @patch('mash.services.uploader.cloud.gce.Provider')
    @patch('mash.services.uploader.cloud.gce.get_driver')
    @patch('mash.services.uploader.cloud.gce.GoogleStorageDriver')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_storage_driver, mock_get_driver, mock_provider
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle
        compute_engine = MagicMock()
        mock_get_driver.return_value = compute_engine
        compute_driver = Mock()
        compute_engine.return_value = compute_driver
        storage_driver = Mock()
        mock_storage_driver.return_value = storage_driver

        assert self.uploader.upload() == ('sles-12-sp4-v20180909', 'region')

        storage_driver.get_container.assert_called_once_with('images')
        assert storage_driver.upload_object_via_stream.call_count == 1

        compute_driver.ex_create_image.assert_called_once_with(
            'sles-12-sp4-v20180909',
            'https://www.googleapis.com/storage/v1/b/images/o/'
            'sles-12-sp4-v20180909.tar.gz',
            description='description 20180909',
            family='sles-12'
        )
