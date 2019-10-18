import pytest

from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.base_job import BaseJob
from mash.utils.json_format import JsonFormat


class TestJobCreatorBaseJob(object):

    def setup(self):
        self.job = BaseJob({
            'job_id': '123',
            'cloud': 'aws',
            'requesting_user': 'test-user',
            'last_service': 'testing',
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

    def test_base_job_post_init(self):
        self.job.post_init()

    @pytest.mark.parametrize('method', [
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
            BaseJob({
                'cloud': 'aws',
                'requesting_user': 'test-user',
                'last_service': 'deprecation',
                'utctime': 'now',
                'image': 'test-image',
                'cloud_image_name': 'test-cloud-image',
                'image_description': 'image description',
                'distro': 'sles',
                'download_url': 'https://download.here',
                'target_account_info': {}
            })

    @patch.object(BaseJob, 'get_testing_regions')
    def test_get_testing_message_cleanup(self, mock_get_testing_regions):
        mock_get_testing_regions.return_value = {}

        message = self.job.get_testing_message()
        assert JsonFormat.json_loads(message)['testing_job']['cleanup_images']

        # Explicit False for no cleanup even on failure
        self.job.cleanup_images = False
        message = self.job.get_testing_message()
        assert JsonFormat.json_loads(message)['testing_job']['cleanup_images'] is False
