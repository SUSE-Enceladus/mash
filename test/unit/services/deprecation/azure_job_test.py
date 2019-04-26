from unittest.mock import Mock
from mash.services.deprecation.azure_job import AzureDeprecationJob


class TestAzureDeprecationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecation',
            'cloud': 'azure',
            'utctime': 'now'
        }
        config = Mock()

        self.job = AzureDeprecationJob(self.job_config, config)
        assert self.job.credentials['status'] == 'no deprecation'

    def test_deprecate(self):
        self.job._run_job()
        assert self.job.status == 'success'
