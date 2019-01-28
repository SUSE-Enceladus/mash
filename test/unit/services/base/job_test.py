from unittest.mock import Mock

from mash.services.mash_job import MashJob


class TestMashJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'testing',
            'provider': 'ec2',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = MashJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'ec2'
        assert job.utctime == 'now'

    def test_send_log(self):
        callback = Mock()

        job = MashJob(**self.job_config)
        job.log_callback = callback
        job.iteration_count = 0

        job.send_log('Starting publish.')

        callback.assert_called_once_with(
            'Pass[0]: Starting publish.',
            {'job_id': '1'},
            True
        )

    def test_job_get_job_id(self):
        job = MashJob(**self.job_config)
        metadata = job.get_job_id()
        assert metadata == {'job_id': '1'}

    def test_job_file_property(self):
        job = MashJob(**self.job_config)
        job.job_file = 'test.file'
        assert job.job_file == 'test.file'

    def test_set_cloud_image_name(self):
        job = MashJob(**self.job_config)
        job.cloud_image_name = 'name123'
        assert job.cloud_image_name == 'name123'

    def test_set_log_callback(self):
        job = MashJob(**self.job_config)
        callback = Mock()
        job.log_callback = callback

        assert job.log_callback == callback
