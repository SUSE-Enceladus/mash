import json
import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.oci_job import OCIJob


@patch.object(OCIJob, '__init__')
def test_oci_job_missing_keys(mock_init):
    mock_init.return_value = None

    job = OCIJob({
        'job_id': '123',
        'cloud': 'oci',
        'requesting_user': 'test-user',
        'last_service': 'deprecation',
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


@patch.object(OCIJob, '__init__')
def test_oci_job_testing_message(mock_init):
    mock_init.return_value = None

    job = OCIJob({
        'job_id': '123',
        'cloud': 'oci',
        'requesting_user': 'test-user',
        'last_service': 'deprecation',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'distro': 'sles',
        'download_url': 'https://download.here',
        'operating_system': 'SLES',
        'operating_system_version': '12SP5'
    })
    job.kwargs = {
        'cloud_account': 'acnt1',
        'cloud': 'oci',
        'region': 'us-phoenix-1',
        'bucket': 'images2',
        'availability_domain': 'Omic:PHX-AD-1',
        'compartment_id': 'ocid1.compartment.oc1..',
        'oci_user_id': 'ocid1.user.oc1..',
        'tenancy': 'ocid1.tenancy.oc1..',
        'operating_system': 'SLES',
        'operating_system_version': '12SP5'
    }
    job.cloud = 'oci'
    job.tests = ['test1']
    job.distro = 'sles'
    job.instance_type = 'VM.Standard2.1'
    job.cloud_architecture = 'x86_64'
    job.base_message = {}

    # Test explicit no cleanup images
    job.last_service = 'deprecation'
    job.cleanup_images = False

    job.post_init()

    testing_message = json.loads(job.get_testing_message())
    assert testing_message['testing_job']['cleanup_images'] is False

    # Test cleanup images on testing only
    job.last_service = 'testing'
    job.cleanup_images = True

    job.post_init()

    testing_message = json.loads(job.get_testing_message())
    assert testing_message['testing_job']['cleanup_images'] is True
