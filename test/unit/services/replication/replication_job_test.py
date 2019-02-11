from pytest import raises
from unittest.mock import Mock, patch

from mash.services.replication.replication_job import ReplicationJob


class TestReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'replication',
            'cloud': 'ec2',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = ReplicationJob(**self.job_config)

        assert job.id == '1'
        assert job.cloud == 'ec2'
        assert job.utctime == 'now'

    def test_replicate(self):
        job = ReplicationJob(**self.job_config)
        with raises(NotImplementedError):
            job._replicate()

    def test_source_regions(self):
        job = ReplicationJob(**self.job_config)
        job.source_regions = {'west': 'ami-123'}
        assert job.source_regions['west'] == 'ami-123'

    @patch.object(ReplicationJob, '_replicate')
    def test_replicate_image(self, mock_replicate):
        job = ReplicationJob(**self.job_config)
        job.log_callback = Mock()
        job.process_job()

        mock_replicate.assert_called_once_with()
