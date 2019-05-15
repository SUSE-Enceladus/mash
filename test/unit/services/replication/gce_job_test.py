from unittest.mock import Mock

from mash.services.replication.gce_job import GCEReplicationJob


class TestGCEReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'replication',
            'cloud': 'gce',
            'utctime': 'now'
        }
        self.config = Mock()
        self.job = GCEReplicationJob(self.job_config, self.config)

    def test_replicate(self):
        self.job.run_job()
