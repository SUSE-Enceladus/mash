from pytest import raises
from unittest.mock import Mock, patch
from mash.services.job_factory import JobFactory
from mash.mash_exceptions import MashJobException
from mash.services.testing.gce_job import GCETestingJob


@patch.object(GCETestingJob, '__init__')
def test_job_factory_create(mock_job_init):
    service_config = Mock()
    job_config = {}

    mock_job_init.return_value = None

    value = JobFactory.create_job(
        'gce', 'testing', job_config, service_config
    )
    assert isinstance(value, GCETestingJob)


def test_job_factory_create_invalid_cloud():
    service_config = Mock()
    job_config = {}

    with raises(MashJobException):
        JobFactory.create_job('fake', 'testing', job_config, service_config)


@patch.object(GCETestingJob, '__init__')
def test_job_factory_create_invalid_config(mock_job_init):
    service_config = Mock()
    job_config = {}

    mock_job_init.side_effect = Exception('Invalid parameters')

    with raises(MashJobException):
        JobFactory.create_job('gce', 'testing', job_config, service_config)
