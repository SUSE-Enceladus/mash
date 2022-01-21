import json
import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.gce_job import GCEJob


@patch.object(GCEJob, '__init__')
def test_gce_job_missing_keys(mock_init):
    mock_init.return_value = None

    job = GCEJob({
        'job_id': '123',
        'cloud': 'gce',
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


@patch.object(GCEJob, '__init__')
def test_gce_job_test_message(mock_init):
    mock_init.return_value = None

    job = GCEJob({
        'job_id': '123',
        'cloud': 'gce',
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
        'bucket': 'images',
        'cloud': 'gce',
        'region': 'westus',
        'testing_account': None
    }
    job.cloud = 'gce'
    job.tests = ['test1']
    job.distro = 'sles'
    job.instance_type = 'b1'
    job.ssh_user = 'root'
    job.cloud_architecture = 'x86_64'
    job.test_fallback = False
    job.test_fallback_regions = None
    job.boot_firmware = ['uefi']
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
