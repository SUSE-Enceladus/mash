from mash.services.publisher.gce_job import GCEPublisherJob


class TestGCEPublisherJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publisher',
            'provider': 'ec2',
            'publish_regions': [],
            'utctime': 'now'
        }

        self.job = GCEPublisherJob(**self.job_config)

    def test_publish(self):
        self.job._publish()
