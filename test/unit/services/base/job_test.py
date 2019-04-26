from pytest import raises
from unittest.mock import Mock, patch

from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashJobException


class TestMashJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'cloud': 'ec2',
            'utctime': 'now'
        }
        self.config = Mock()

    def test_missing_key(self):
        del self.job_config['cloud']

        with raises(MashJobException):
            MashJob(self.job_config, self.config)

    def test_valid_job(self):
        job = MashJob(self.job_config, self.config)

        assert job.id == '1'
        assert job.cloud == 'ec2'
        assert job.utctime == 'now'

    def test_send_log(self):
        callback = Mock()

        job = MashJob(self.job_config, self.config)
        job.log_callback = callback
        job.iteration_count = 0

        job.send_log('Starting publish.')

        callback.assert_called_once_with(
            'Pass[0]: Starting publish.',
            {'job_id': '1'},
            True
        )

    def test_run_job(self):
        job = MashJob(self.job_config, self.config)

        with raises(NotImplementedError):
            job._run_job()

    def test_job_get_job_id(self):
        job = MashJob(self.job_config, self.config)
        metadata = job.get_job_id()
        assert metadata == {'job_id': '1'}

    def test_job_file_property(self):
        job = MashJob(self.job_config, self.config)
        job.job_file = 'test.file'
        assert job.job_file == 'test.file'

    def test_set_cloud_image_name(self):
        job = MashJob(self.job_config, self.config)
        job.cloud_image_name = 'name123'
        assert job.cloud_image_name == 'name123'

    def test_set_log_callback(self):
        job = MashJob(self.job_config, self.config)
        callback = Mock()
        job.log_callback = callback

        assert job.log_callback == callback

    @patch.object(MashJob, '_run_job')
    def test_process_job(self, mock_run_job):
        job = MashJob(self.job_config, self.config)
        job.process_job()
        mock_run_job.assert_called_once_with()
