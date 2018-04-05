from mash.services.jobcreator.config import JobCreatorConfig


class TestJobCreatorConfig(object):
    def setup(self):
        self.empty_config = JobCreatorConfig(
            '../data/empty_job_creator_config.yml'
        )

    def test_job_creator_get_log_file(self):
        assert self.empty_config.get_log_file('jobcreator') == \
            '/var/log/mash/jobcreator_service.log'

    def test_job_creator_get_accounts_file(self):
        assert self.empty_config.get_accounts_file() == \
            '/etc/mash/accounts.json'
