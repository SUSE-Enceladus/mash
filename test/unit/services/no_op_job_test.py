from unittest.mock import Mock

from mash.services.no_op_job import NoOpJob


class TestNoOpJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecation',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }
        self.config = Mock()
        self.job = NoOpJob(self.job_config, self.config)
        self.job._log_callback = Mock()

    def test_run_job(self):
        self.job.run_job()
