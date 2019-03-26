import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.base_job import BaseJob


class TestJobCreatorBaseJob(object):

    @patch.object(BaseJob, 'get_account_info')
    def setup(self, mock_get_account_info):
        self.job = BaseJob(
            {}, {}, {
                'job_id': '123',
                'cloud': 'aws',
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

    def test_base_job_post_init(self):
        self.job.post_init()

    @pytest.mark.parametrize('method', [
        ('get_account_info'),
        ('get_deprecation_message'),
        ('get_publisher_message'),
        ('get_replication_message'),
        ('get_replication_source_regions'),
        ('get_testing_regions'),
        ('get_uploader_regions')
    ])
    def test_base_job_not_impl_methods(self, method):
        with pytest.raises(NotImplementedError):
            getattr(self.job, method)()

    def test_base_job_init_missing_key(self):
        with pytest.raises(MashJobCreatorException):
            BaseJob(
                {}, {}, {
                    'cloud': 'aws',
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
