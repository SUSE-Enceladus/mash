from mash.services.base_defaults import Defaults


def test_get_config():
    config = Defaults.get_config()
    assert config == '/etc/mash/mash_config.yaml'


def test_get_job_directory():
    job_directory = Defaults.get_job_directory('testing')
    assert job_directory == '/var/lib/mash/testing_jobs/'


def test_get_log_directory():
    log_directory = Defaults.get_log_directory()
    assert log_directory == '/var/log/mash/'


def test_get_azure_max_workers():
    max_workers = Defaults.get_azure_max_workers()
    assert max_workers == 5
