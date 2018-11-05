from pytest import raises
from unittest.mock import Mock, patch

from mash.services.replication.job import ReplicationJob


class TestReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'provider': 'ec2',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = ReplicationJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'ec2'
        assert job.utctime == 'now'

    def test_job_get_metadata(self):
        job = ReplicationJob(**self.job_config)
        metadata = job.get_metadata()
        assert metadata == {'job_id': '1'}

    def test_replicate(self):
        job = ReplicationJob(**self.job_config)
        with raises(NotImplementedError):
            job._replicate()

    def test_send_log(self):
        callback = Mock()

        job = ReplicationJob(**self.job_config)
        job.log_callback = callback
        job.iteration_count = 0

        job.send_log('Starting replicate.')

        callback.assert_called_once_with(
            'Pass[0]: Starting replicate.',
            {'job_id': '1'},
            True
        )

    def test_set_cloud_image_name(self):
        job = ReplicationJob(**self.job_config)
        job.set_cloud_image_name('name123')
        assert job.cloud_image_name == 'name123'

    def test_set_log_callback(self):
        test = Mock()

        job = ReplicationJob(**self.job_config)
        job.set_log_callback(test.method)

        assert job.log_callback == test.method

    @patch.object(ReplicationJob, '_replicate')
    def test_replicate_image(self, mock_replicate):
        job = ReplicationJob(**self.job_config)
        job.log_callback = Mock()
        job.replicate_image()

        mock_replicate.assert_called_once_with()
