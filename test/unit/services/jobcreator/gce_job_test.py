import pytest

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.gce_job import GCEJob


def test_gce_job_publish_acnt():
    account_info = {
        'acnt1': {
            'name': 'actn1',
            'bucket': 'test',
            'region': 'us-west1-a',
            'is_publishing_account': True
        }
    }

    with pytest.raises(MashJobCreatorException):
        GCEJob(
            account_info, {}, {
                'job_id': '123',
                'cloud': 'gce',
                'requesting_user': 'test-user',
                'last_service': 'deprecation',
                'utctime': 'now',
                'image': 'test-image',
                'cloud_image_name': 'test-cloud-image',
                'cloud_accounts': [{'name': 'acnt1'}],
                'image_description': 'image description',
                'distro': 'sles',
                'download_url': 'https://download.here'
            }
        )
