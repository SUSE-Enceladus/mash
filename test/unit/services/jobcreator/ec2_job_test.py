from unittest.mock import patch

from mash.services.jobcreator.ec2_job import EC2Job
from mash.utils.json_format import JsonFormat


@patch.object(EC2Job, 'get_test_regions')
def test_get_test_message_cleanup(mock_get_test_regions):
    mock_get_test_regions.return_value = {}

    job = EC2Job({
        'job_id': '123',
        'cloud': 'ec2',
        'requesting_user': 'test-user',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'distro': 'sles',
        'download_url': 'https://download.here',
        'cleanup_images': True,
        'test_fallback_regions': [],
        'target_account_info': {}
    })

    message = job.get_test_message()
    assert JsonFormat.json_loads(message)['test_job']['cleanup_images']

    # Explicit False for no cleanup even on failure
    job.cleanup_images = False
    message = job.get_test_message()
    assert JsonFormat.json_loads(message)['test_job']['cleanup_images'] is False
