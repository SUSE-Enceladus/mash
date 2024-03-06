from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.create.gce_job import GCECreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestGCECreateJob(object):
    def setup_method(self):
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
        self.complete_job_doc = {
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

        self.job = GCECreateJob(self.complete_job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'upload',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            GCECreateJob(job_doc, self.config)

    @patch('mash.services.create.gce_job.get_gce_image')
    @patch('mash.services.create.gce_job.create_gce_image')
    @patch('mash.services.create.gce_job.create_gce_rollout')
    @patch('mash.services.create.gce_job.delete_gce_image')
    @patch('mash.services.create.gce_job.get_gce_compute_driver')
    @patch('builtins.open')
    def test_create_default(
        self,
        mock_open,
        mock_get_driver,
        mock_delete_image,
        mock_create_rollout,
        mock_create_image,
        mock_get_image
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        compute_driver = Mock()
        mock_get_driver.return_value = compute_driver

        rollout = {'defaultRolloutTime': '2021-01-01T00:00:00Z'}
        mock_create_rollout.return_value = rollout

        self.job.status_msg['cloud_image_name'] = 'sles-12-sp4-v20180909'
        self.job.status_msg['object_name'] = 'sles-12-sp4-v20180909.tar.gz'
        self.job.run_job()

        mock_delete_image.assert_called_once_with(
            compute_driver,
            'projectid',
            'sles-12-sp4-v20180909'
        )
        mock_create_rollout.assert_called_once_with(
            compute_driver,
            'projectid'
        )
        mock_create_image.assert_called_once_with(
            compute_driver,
            'projectid',
            'sles-12-sp4-v20180909',
            'description 20180909',
            'https://www.googleapis.com/storage/v1/b/images/o/sles-12-sp4-v20180909.tar.gz',
            family='sles-12',
            guest_os_features=['UEFI_COMPATIBLE'],
            rollout=rollout,
            arch='x86_64'
        )

    @patch('mash.services.create.gce_job.get_gce_image')
    @patch('mash.services.create.gce_job.create_gce_image')
    @patch('mash.services.create.gce_job.delete_gce_image')
    @patch('mash.services.create.gce_job.get_gce_compute_driver')
    @patch('builtins.open')
    def test_create_aarch64(
        self,
        mock_open,
        mock_get_driver,
        mock_delete_image,
        mock_create_image,
        mock_get_image
    ):
        self.complete_job_doc['cloud_architecture'] = 'aarch64'
        self.complete_job_doc['cloud_image_name'] = 'sles-15-sp4-v20210731'
        self.complete_job_doc['family'] = 'sles-15-arm64'
        self.complete_job_doc['skip_rollout'] = True
        job = GCECreateJob(self.complete_job_doc, self.config)
        job._log_callback = Mock()
        job.credentials = self.credentials
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        compute_driver = Mock()
        mock_get_driver.return_value = compute_driver

        job.status_msg['cloud_image_name'] = 'sles-15-sp4-v20210731'
        job.status_msg['object_name'] = 'sles-15-sp4-v20210731.tar.gz'
        job.run_job()

        mock_delete_image.assert_called_once_with(
            compute_driver,
            'projectid',
            'sles-15-sp4-v20210731'
        )
        mock_create_image.assert_called_once_with(
            compute_driver,
            'projectid',
            'sles-15-sp4-v20210731',
            'description 20180909',
            'https://www.googleapis.com/storage/v1/b/images/o/sles-15-sp4-v20210731.tar.gz',
            family='sles-15-arm64',
            guest_os_features=['UEFI_COMPATIBLE'],
            rollout=None,
            arch='arm64'
        )
