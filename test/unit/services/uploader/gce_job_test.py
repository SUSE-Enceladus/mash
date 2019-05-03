from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.uploader.gce_job import GCEUploaderJob
from mash.mash_exceptions import MashUploadException
from mash.services.uploader.config import UploaderConfig


class TestGCEUploaderJob(object):
    def setup(self):
        self.config = UploaderConfig(
            config_file='../data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
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
        }
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'cloud': 'gce',
            'utctime': 'now',
            'target_regions': {
                'us-west1-a': {
                    'account': 'test',
                    'bucket': 'images',
                    'family': 'sles-12'
                }
            },
            'cloud_image_name': 'sles-12-sp4-v20180909',
            'image_description': 'description 20180909'
        }

        self.job = GCEUploaderJob(job_doc, self.config)
        self.job.image_file = ['sles-12-sp4-v20180909.tar.gz']
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            GCEUploaderJob(job_doc, self.config)

        job_doc['target_regions'] = {'us-west1-a': {'account': 'test'}}
        with raises(MashUploadException):
            GCEUploaderJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'test image 123'
        with raises(MashUploadException):
            GCEUploaderJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'sles-11'
        job_doc['image_description'] = 'test image description'
        with raises(MashUploadException):
            GCEUploaderJob(job_doc, self.config)

    @patch('mash.services.uploader.gce_job.NamedTemporaryFile')
    @patch('mash.services.uploader.gce_job.Provider')
    @patch('mash.services.uploader.gce_job.get_driver')
    @patch('mash.services.uploader.gce_job.GoogleStorageDriver')
    @patch('builtins.open')
    def test_upload(
        self, mock_open, mock_storage_driver, mock_get_driver, mock_provider,
        mock_NamedTemporaryFile
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

        tempfile = Mock()
        tempfile.name = 'tempfile'
        mock_NamedTemporaryFile.return_value = tempfile

        self.job._run_job()

        storage_driver.get_container.assert_called_once_with('images')
        assert storage_driver.upload_object_via_stream.call_count == 1

        compute_driver.ex_create_image.assert_called_once_with(
            'sles-12-sp4-v20180909',
            'https://www.googleapis.com/storage/v1/b/images/o/'
            'sles-12-sp4-v20180909.tar.gz',
            description='description 20180909',
            family='sles-12'
        )
