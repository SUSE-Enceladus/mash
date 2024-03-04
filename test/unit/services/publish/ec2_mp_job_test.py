from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashPublishException
from mash.services.publish.ec2_mp_job import EC2MPPublishJob


class TestEC2MPPublishJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'last_service': 'publish',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'entity_id': '123',
            'version_title': 'openSUSE Leap 15.3 - v20220114',
            'release_notes': 'https://en.opensuse.org/openSUSE:Release_Notes',
            'access_role_arn': '',
            'os_name': 'OTHERLINUX',
            'os_version': '15.3',
            'usage_instructions': 'Login using SSH...',
            'recommended_instance_type': 't3.medium',
            'publish_regions': {'test-aws': 'us-east-2'},
            'share_with': '123456789',
            'allow_copy': 'image',
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
        self.job.status_msg['cloud_image_name'] = 'image_name_v20220202'
        self.job.status_msg['source_regions'] = {'us-east-2': 'image-id'}
        self.job.status_msg['publish_date'] = '20220114'
        self.job._log_callback = Mock()

    def test_publish_ec2_missing_key(self):
        del self.job_config['publish_regions']

        with raises(MashPublishException):
            EC2MPPublishJob(self.job_config, self.config)

    @patch('mash.services.publish.ec2_mp_job.get_session')
    @patch('mash.services.publish.ec2_mp_job.start_mp_change_set')
    @patch('mash.services.publish.ec2_mp_job.EC2PublishImage')
    def test_publish(
        self,
        mock_ec2_publish_image,
        mock_start_change_set,
        mock_get_session
    ):
        publish = Mock()
        mock_ec2_publish_image.return_value = publish
        mock_start_change_set.return_value = {'ChangeSetId': '123'}

        self.job.run_job()

        mock_ec2_publish_image.assert_called_once_with(
            access_key='123456',
            allow_copy='image',
            image_name='image_name_v20220202',
            secret_key='654321',
            visibility='123456789',
            log_callback=self.job._log_callback
        )

        publish.set_region.assert_called_once_with('us-east-2')

        assert publish.publish_images.call_count == 1
        assert self.job.status == 'success'

    @patch('mash.services.publish.ec2_mp_job.start_mp_change_set')
    @patch('mash.services.publish.ec2_mp_job.EC2PublishImage')
    def test_publish_exception(
        self,
        mock_ec2_publish_image,
        mock_start_change_set
    ):
        publish = Mock()
        publish.publish_images.side_effect = Exception('Failed to publish.')
        mock_ec2_publish_image.return_value = publish
        mock_start_change_set.return_value = {'ChangeSetId': '123'}

        with raises(MashPublishException):
            self.job.run_job()
