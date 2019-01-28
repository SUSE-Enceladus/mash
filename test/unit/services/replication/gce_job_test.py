from mash.services.replication.gce_job import GCEReplicationJob


class TestGCEReplicationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'image_description': 'test image',
            'last_service': 'replication',
            'provider': 'gce',
            'utctime': 'now',
            "replication_source_regions": {}
        }
        self.job = GCEReplicationJob(**self.job_config)

    def test_replicate(self):
        self.job._replicate()
