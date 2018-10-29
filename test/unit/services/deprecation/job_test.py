from pytest import raises
from unittest.mock import Mock, patch

from mash.services.deprecation.job import DeprecationJob


class TestDeprecationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'ec2',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = DeprecationJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'ec2'
        assert job.utctime == 'now'

    def test_job_get_metadata(self):
        job = DeprecationJob(**self.job_config)
        metadata = job.get_metadata()
        assert metadata == {'job_id': '1'}

    def test_deprecate(self):
        job = DeprecationJob(**self.job_config)
        with raises(NotImplementedError):
            job._deprecate()

    def test_send_log(self):
        callback = Mock()

        job = DeprecationJob(**self.job_config)
        job.log_callback = callback
        job.iteration_count = 0

        job.send_log('Starting deprecation.')

        callback.assert_called_once_with(
            'Pass[0]: Starting deprecation.',
            {'job_id': '1'},
            True
        )

    def test_set_cloud_image_name(self):
        job = DeprecationJob(**self.job_config)
        job.set_cloud_image_name('name123')
        assert job.cloud_image_name == 'name123'

    def test_set_log_callback(self):
        test = Mock()

        job = DeprecationJob(**self.job_config)
        job.set_log_callback(test.method)

        assert job.log_callback == test.method

    @patch.object(DeprecationJob, '_deprecate')
    def test_deprecate_image(self, mock_deprecate):
        job = DeprecationJob(**self.job_config)
        job.log_callback = Mock()
        job.deprecate_image()

        mock_deprecate.assert_called_once_with()
