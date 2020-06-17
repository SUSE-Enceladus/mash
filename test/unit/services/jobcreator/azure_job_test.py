import json
import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.azure_job import AzureJob


@patch.object(AzureJob, '__init__')
def test_azure_job_missing_keys(mock_init):
    mock_init.return_value = None

    job = AzureJob({
        'job_id': '123',
        'cloud': 'azure',
        'requesting_user': 'test-user',
        'last_service': 'deprecate',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'distro': 'sles',
        'download_url': 'https://download.here'
    })
    job.kwargs = {}

    with pytest.raises(MashJobCreatorException):
        job.post_init()


@patch.object(AzureJob, '__init__')
def test_azure_job_cleanup(mock_init):
    mock_init.return_value = None

    job = AzureJob({
        'job_id': '123',
        'cloud': 'azure',
        'requesting_user': 'test-user',
        'last_service': 'deprecate',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'distro': 'sles',
        'download_url': 'https://download.here'
    })
    job.kwargs = {
        'cloud_account': 'acnt1',
        'label': 'Great Image',
        'offer_id': 'sles',
        'publisher_id': 'suse',
        'sku': 'sp1',
        'cloud': 'azure'
    }
    job.cloud = 'azure'
    job.tests = ['test1']
    job.distro = 'sles'
    job.instance_type = 'b1'
    job.cloud_architecture = 'x86_64'
    job.base_message = {}

    # Test explicit no cleanup images
    job.last_service = 'deprecate'
    job.cleanup_images = False

    job.post_init()

    test_message = json.loads(job.get_test_message())
    assert test_message['test_job']['cleanup_images'] is False

    # Test cleanup images on test only
    job.last_service = 'test'
    job.cleanup_images = True

    job.post_init()

    test_message = json.loads(job.get_test_message())
    assert test_message['test_job']['cleanup_images'] is True
