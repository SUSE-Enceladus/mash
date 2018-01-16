from mash.services.base_defaults import Defaults


def test_get_job_directory():
    job_directory = Defaults.get_job_directory('testing')
    assert job_directory == '/var/lib/mash/testing_jobs/'
