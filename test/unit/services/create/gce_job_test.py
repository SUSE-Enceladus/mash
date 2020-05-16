from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.create.gce_job import GCECreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestGCECreateJob(object):
    def setup(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
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
            'last_service': 'create',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'utctime': 'now',
            'family': 'sles-12',
            'guest_os_features': ['UEFI_COMPATIBLE'],
            'region': 'us-west1-a',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-12-sp4-v20180909',
            'image_description': 'description 20180909'
        }

        self.job = GCECreateJob(job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'uploader',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            GCECreateJob(job_doc, self.config)

    @patch('mash.services.create.gce_job.Provider')
    @patch('mash.services.create.gce_job.get_driver')
    @patch('builtins.open')
    def test_create(
        self, mock_open, mock_get_driver, mock_provider
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        compute_engine = MagicMock()
        mock_get_driver.return_value = compute_engine

        compute_driver = Mock()
        compute_engine.return_value = compute_driver

        self.job.source_regions = {
            'cloud_image_name': 'sles-12-sp4-v20180909',
            'object_name': 'sles-12-sp4-v20180909.tar.gz'
        }
        self.job.run_job()

        compute_driver.ex_create_image.assert_called_once_with(
            'sles-12-sp4-v20180909',
            'https://www.googleapis.com/storage/v1/b/images/o/'
            'sles-12-sp4-v20180909.tar.gz',
            description='description 20180909',
            wait_for_completion=True,
            family='sles-12',
            guest_os_features=['UEFI_COMPATIBLE']
        )
