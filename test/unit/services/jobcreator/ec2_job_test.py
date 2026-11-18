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
        'target_account_info': {},
        'ssh_user': 'root'
    })

    message = job.get_test_message()
    assert JsonFormat.json_loads(message)['test_job']['cleanup_images']

    # Explicit False for no cleanup even on failure
    job.cleanup_images = False
    message = job.get_test_message()
    assert JsonFormat.json_loads(message)['test_job']['cleanup_images'] is False


@patch.object(EC2Job, 'get_test_regions')
def test_get_mp_publish_message(mock_get_test_regions):
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
        'target_account_info': {},
        'publish_in_marketplace': True,
        'entity_id': '123',
        'ssh_user': 'root'
    })
    job.target_account_info = {'us-east-2': {'account': 'acnt1'}}

    message = job.get_publish_message()
    assert JsonFormat.json_loads(message)['publish_job']['entity_id'] == '123'


@patch.object(EC2Job, 'get_test_regions')
def test_get_mp_deprecate_message(mock_get_test_regions):
    mock_get_test_regions.return_value = {}

    job = EC2Job({
        'job_id': '123',
        'cloud': 'ec2',
        'requesting_user': 'test-user',
        'last_service': 'deprecate',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'old_cloud_image_name': 'old-test-cloud-image',
        'image_description': 'image description',
        'distro': 'sles',
        'download_url': 'https://download.here',
        'cleanup_images': True,
        'test_fallback_regions': [],
        'target_account_info': {},
        'publish_in_marketplace': True,
        'entity_id': '123',
        'ssh_user': 'root'
    })
    job.target_account_info = {'us-east-2': {'account': 'acnt1'}}

    message = job.get_deprecate_message()
    assert JsonFormat.json_loads(message)['deprecate_job']['entity_id'] == '123'


@patch.object(EC2Job, 'get_create_regions')
def test_get_create_message(mock_get_create_regions):
    mock_get_create_regions.return_value = {'us-east-2': {'account': 'acnt1'}}

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
        'target_account_info': {},
        'publish_in_marketplace': True,
        'entity_id': '123',
        'ssh_user': 'root',
        'imds_version': 'v2.0',
    })

    message = job.get_create_message()
    assert JsonFormat.json_loads(message)['create_job']['imds_version'] == \
        'v2.0'


def test_get_create_message_upload_options():
    job = EC2Job({
        'job_id': '123',
        'cloud': 'ec2',
        'requesting_user': 'test-user',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'download_url': 'https://download.here',
        'target_account_info': {},
        'upload_workers': 4,
        'upload_retries': 6,
        'upload_timeout': 120,
        'launch_inst_type': 'm1.large'
    })

    create_job = JsonFormat.json_loads(job.get_create_message())['create_job']
    assert create_job['upload_workers'] == 4
    assert create_job['upload_retries'] == 6
    assert create_job['upload_timeout'] == 120
    assert create_job['launch_inst_type'] == 'm1.large'

    # Not sent when not set so ec2imgutils keeps its defaults
    job.upload_workers = None
    job.upload_retries = None
    job.upload_timeout = None
    create_job = JsonFormat.json_loads(job.get_create_message())['create_job']
    assert 'upload_workers' not in create_job
    assert 'upload_retries' not in create_job
    assert 'upload_timeout' not in create_job


def test_get_create_regions():
    job = EC2Job({
        'job_id': '123',
        'cloud': 'ec2',
        'requesting_user': 'test-user',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'download_url': 'https://download.here',
        'billing_codes': 'bp-123',
        'use_root_swap': True,
        'target_account_info': {
            'us-east-1': {
                'account': 'acnt1',
                'target_regions': ['us-east-1', 'us-east-2'],
                'helper_image': 'ami-123',
                'subnet': 'subnet-123'
            }
        }
    })

    assert job.get_create_regions() == {
        'us-east-1': {
            'account': 'acnt1',
            'helper_image': 'ami-123',
            'billing_codes': 'bp-123',
            'use_root_swap': True,
            'subnet': 'subnet-123',
            'regions': ['us-east-1', 'us-east-2']
        }
    }

    # Without root swap and without helper image or subnet
    job = EC2Job({
        'job_id': '123',
        'cloud': 'ec2',
        'requesting_user': 'test-user',
        'last_service': 'test',
        'utctime': 'now',
        'image': 'test-image',
        'cloud_image_name': 'test-cloud-image',
        'image_description': 'image description',
        'download_url': 'https://download.here',
        'target_account_info': {
            'us-east-1': {
                'account': 'acnt1',
                'target_regions': ['us-east-1']
            }
        }
    })

    info = job.get_create_regions()['us-east-1']
    assert info['use_root_swap'] is False
    assert info['helper_image'] is None
    assert info['subnet'] is None
