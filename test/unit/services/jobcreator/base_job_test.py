import pytest

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.base_job import BaseJob


class TestJobCreatorBaseJob(object):

    def setup_method(self):
        self.job = BaseJob({
            'job_id': '123',
            'cloud': 'aws',
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
            'boot_firmware': ['bios']
        })

    def test_base_job_post_init(self):
        self.job.post_init()

    @pytest.mark.parametrize('method', [
        ('get_deprecate_message'),
        ('get_publish_message'),
        ('get_replicate_message'),
        ('get_upload_message'),
        ('get_test_message'),
        ('get_create_message')
    ])
    def test_base_job_not_impl_methods(self, method):
        with pytest.raises(NotImplementedError):
            getattr(self.job, method)()

    def test_base_job_init_missing_key(self):
        with pytest.raises(MashJobCreatorException):
            BaseJob({
                'cloud': 'aws',
                'requesting_user': 'test-user',
                'last_service': 'deprecate',
                'utctime': 'now',
                'image': 'test-image',
                'cloud_image_name': 'test-cloud-image',
                'image_description': 'image description',
                'distro': 'sles',
                'download_url': 'https://download.here',
                'target_account_info': {}
            })

    def test_base_job_raw_upload_only(self):
        BaseJob({
            'job_id': '123',
            'cloud': 'aws',
            'requesting_user': 'test-user',
            'last_service': 'upload',
            'utctime': 'now',
            'image': 'test-image',
            'cloud_image_name': 'test-cloud-image',
            'image_description': 'image description',
            'distro': 'sles',
            'download_url': 'https://download.here',
            'target_account_info': {},
            'raw_image_upload_type': 's3bucket'
        })
