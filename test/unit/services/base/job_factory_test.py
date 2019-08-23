from pytest import raises
from unittest.mock import Mock, patch
from mash.services.job_factory import JobFactory
from mash.mash_exceptions import MashJobException
from mash.services.testing.gce_job import GCETestingJob
from mash.services.raw_image_uploader.s3bucket_job import S3BucketUploaderJob


@patch.object(GCETestingJob, '__init__')
def test_job_factory_create(mock_job_init):
    service_config = Mock()
    job_config = {}

    mock_job_init.return_value = None

    value = JobFactory.create_job(
        'gce', 'testing', job_config, service_config
    )
    assert isinstance(value, GCETestingJob)

    job_config = {
        'raw_image_upload_type': 's3bucket',
        'raw_image_upload_account': 'account',
        'raw_image_upload_location': 'location',
        'id': '123',
        'last_service': 'raw_image_uploader',
        'cloud': 'gce',
        'utctime': 'now'
    }
    value = JobFactory.create_job(
        'gce', 'raw_image_uploader', job_config, service_config
    )
    assert isinstance(value, S3BucketUploaderJob)

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
