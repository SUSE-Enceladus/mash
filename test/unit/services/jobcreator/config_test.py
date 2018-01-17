from mash.services.jobcreator.config import JobCreatorConfig


class TestJobCreatorConfig(object):
    def setup(self):
        self.empty_config = JobCreatorConfig(
            '../data/empty_job_creator_config.yml'
        )

    def test_job_creator_config_data(self):
        assert self.empty_config.config_data

    def test_job_creator_get_log_file(self):
        assert self.empty_config.get_log_file() == \
            '/var/log/mash/job_creator_service.log'
