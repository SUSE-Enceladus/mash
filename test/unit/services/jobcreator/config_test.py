from mash.services.jobcreator.config import JobCreatorConfig


class TestJobCreatorConfig(object):
    def setup(self):
        self.empty_config = JobCreatorConfig(
            'test/data/empty_mash_config.yaml'
        )

    def test_job_creator_get_log_file(self):
        assert self.empty_config.get_log_file('jobcreator') == \
            '/var/log/mash/jobcreator_service.log'
