from unittest.mock import Mock

from mash.services.raw_image_uploader.skip_raw_image_uploader_job import SkipRawImageUploaderJob


class TestSkipRawImageUploaderJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'raw_image_uploader',
            'requesting_user': 'user1',
            'cloud': 'gce',
            'utctime': 'now'
        }
        self.config = Mock()
        self.job = SkipRawImageUploaderJob(self.job_config, self.config)

    def test_replicate(self):
        self.job.run_job()
