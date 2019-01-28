from mash.services.replication.gce_job import GCEReplicationJob


class TestGCEReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'replication',
            'provider': 'gce',
            'utctime': 'now'
        }
        self.job = GCEReplicationJob(**self.job_config)

    def test_replicate(self):
        self.job._replicate()
