from mash.services.deprecation.azure_job import AzureDeprecationJob


class TestAzureDeprecationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publisher',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        self.job = AzureDeprecationJob(**self.job_config)

    def test_publish(self):
        self.job._deprecate()
