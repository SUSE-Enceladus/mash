from pytest import raises
from unittest.mock import Mock, patch
from mash.services.job_factory import BaseJobFactory
from mash.mash_exceptions import MashJobException
from mash.services.testing.gce_job import GCETestingJob
from mash.services.no_op_job import NoOpJob


@patch.object(GCETestingJob, '__init__')
def test_job_factory_create(mock_job_init):
    service_config = Mock()
    job_config = {'cloud': 'gce'}

    mock_job_init.return_value = None

    job_factory = BaseJobFactory(
        service_name='testing',
        job_types={'gce': GCETestingJob}
    )

    value = job_factory.create_job(job_config, service_config)
    assert isinstance(value, GCETestingJob)


def test_job_factory_create_no_type():
    service_config = Mock()
    job_config = {}

    job_factory = BaseJobFactory(
        service_name='testing',
        job_types={'gce': GCETestingJob}
    )

    with raises(MashJobException):
        job_factory.create_job(job_config, service_config)


@patch.object(NoOpJob, '__init__')
def test_job_factory_skip(mock_job_init):
    service_config = Mock()
    job_config = {'cloud': None}

    mock_job_init.return_value = None

    job_factory = BaseJobFactory(
        service_name='testing',
        job_types={'gce': GCETestingJob},
        can_skip=True
    )

    job = job_factory.create_job(job_config, service_config)
    assert isinstance(job, NoOpJob)


def test_job_factory_create_invalid_cloud():
    service_config = Mock()
    job_config = {'cloud': 'fake'}

    job_factory = BaseJobFactory(
        service_name='testing',
        job_types={'gce': GCETestingJob}
    )

    with raises(MashJobException):
        job_factory.create_job(job_config, service_config)


@patch.object(GCETestingJob, '__init__')
def test_job_factory_create_invalid_config(mock_job_init):
    service_config = Mock()
    job_config = {'cloud': 'gce'}

    mock_job_init.side_effect = Exception('Invalid parameters')

    job_factory = BaseJobFactory(
        service_name='testing',
        job_types={'gce': GCETestingJob}
    )

    with raises(MashJobException):
        job_factory.create_job(job_config, service_config)
