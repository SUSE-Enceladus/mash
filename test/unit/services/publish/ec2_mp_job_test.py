from pytest import raises
from unittest.mock import Mock

from mash.mash_exceptions import MashPublishException
from mash.services.publish.ec2_mp_job import EC2MPPublishJob


class TestEC2MPPublishJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'publish_regions': [
                {
                    'account': 'test-aws',
                    'target_regions': ['us-east-2']
                }
            ],
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = EC2MPPublishJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'test-aws': {
                'access_key_id': '123456',
                'secret_access_key': '654321',
                'ssh_key_name': 'key-123',
                'ssh_private_key': 'key123'
            }
        }
        self.job.status_msg['cloud_image_name'] = 'image_name_123'
        self.job.status_msg['source_regions'] = {'us-east-2': 'image-id'}
        self.job._log_callback = Mock()

    def test_publish_ec2_missing_key(self):
        del self.job_config['publish_regions']

        with raises(MashPublishException):
            EC2MPPublishJob(self.job_config, self.config)

    def test_publish(self):
        self.job.run_job()
        assert self.job.status == 'success'
