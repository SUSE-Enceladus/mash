from unittest.mock import patch

from mash.services.base_defaults import Defaults


@patch('mash.services.base_defaults.os.makedirs')
def test_get_job_directory(mock_makedirs):
    job_directory = Defaults.get_job_directory('testing')
    mock_makedirs.assert_called_once_with(
        '/var/lib/mash/testing_jobs/',
        exist_ok=True
    )
    assert job_directory == '/var/lib/mash/testing_jobs/'
