import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.azure_job import AzureJob


@patch.object(AzureJob, '__init__')
def test_azure_job_missing_keys(mock_init):
    mock_init.return_value = None

    job = AzureJob(
        {}, {}, {
            'job_id': '123',
            'cloud': 'azure',
            'requesting_user': 'test-user',
            'last_service': 'pint',
            'utctime': 'now',
            'image': 'test-image',
            'cloud_image_name': 'test-cloud-image',
            'image_description': 'image description',
            'distro': 'sles',
            'download_url': 'https://download.here'
        }
    )
    job.kwargs = {}

    with pytest.raises(MashJobCreatorException):
        job.post_init()
