from pytest import raises
from unittest.mock import MagicMock, patch, Mock

from mash.services.deprecate.gce_job import GCEDeprecateJob
from mash.mash_exceptions import MashDeprecateException


class TestGCEDeprecateJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecate',
            'cloud': 'gce',
            'requesting_user': 'user1',
            'old_cloud_image_name': 'old_image_123',
            'account': 'test-gce',
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = GCEDeprecateJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'test-gce': {
                'client_email': 'test@gce.com',
                'project_id': '1234567890'
            }
        }
        self.job.status_msg['cloud_image_name'] = 'image_123'

    def test_deprecate_gce_missing_key(self):
        del self.job_config['account']

        with raises(MashDeprecateException):
            GCEDeprecateJob(self.job_config, self.config)

        self.job_config['account'] = 'test-gce'

    @patch('mash.services.deprecate.gce_job.deprecate_gce_image')
    @patch('mash.services.deprecate.gce_job.get_gce_compute_driver')
    def test_deprecate(self, mock_get_driver, mock_deprecate_image):
        compute_driver = MagicMock()
        mock_get_driver.return_value = compute_driver

        self.job.run_job()

        assert mock_deprecate_image.call_count == 1
        assert self.job.status == 'success'
        self.job._log_callback.info.assert_called_once_with(
            'Deprecated image old_image_123.'
        )

    def test_deprecate_no_old_image(self):
        self.job.old_cloud_image_name = None
        self.job.run_job()
        assert self.job.status == 'success'

    @patch('mash.services.deprecate.gce_job.deprecate_gce_image')
    @patch('mash.services.deprecate.gce_job.get_gce_compute_driver')
    def test_deprecate_exception(
        self, mock_get_driver, mock_deprecate_image
    ):
        compute_driver = MagicMock()
        mock_get_driver.return_value = compute_driver

        mock_deprecate_image.side_effect = Exception('Failed!')

        self.job.run_job()

        self.job._log_callback.error.assert_called_once_with(
            'There was an error deprecating image in test-gce: Failed!'
        )
        assert self.job.status == 'failed'
