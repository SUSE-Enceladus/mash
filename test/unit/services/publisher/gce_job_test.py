from unittest.mock import Mock

from mash.services.publisher.gce_job import GCEPublisherJob


class TestGCEPublisherJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publisher',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = GCEPublisherJob(self.job_config, self.config)

    def test_publish(self):
        self.job.run_job()
