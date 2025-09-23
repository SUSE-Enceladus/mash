from pytest import raises
from unittest.mock import Mock, patch

from mash.mash_exceptions import MashDeprecateException
from mash.services.deprecate.ec2_mp_job import EC2MPDeprecateJob


class TestEC2MPDeprecateJob(object):
    def setup_method(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecate',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'entity_id': '123',
            'deprecate_regions': {'test-aws': 'us-east-2'},
            'old_cloud_image_name': 'old-cloud-image-123',
            'utctime': 'now'
        }

        self.config = Mock()
        self.job = EC2MPDeprecateJob(self.job_config, self.config)
        self.job._log_callback = Mock()
        self.job.credentials = {
            'test-aws': {
                'access_key_id': '123456',
                'secret_access_key': '654321',
                'ssh_key_name': 'key-123',
                'ssh_private_key': 'key123'
            }
        }
        self.job.status_msg['add_version_doc'] = {
            'ChangeType': 'AddDeliveryOptions',
            'Entity': {
                'Type': 'AmiProduct@1.0',
                'Identifier': '123'
            },
            'Details': '{"new": "version"}'
        }
        self.job._log_callback = Mock()

    def test_deprecate_ec2_missing_key(self):
        del self.job_config['deprecate_regions']

        with raises(MashDeprecateException):
            EC2MPDeprecateJob(self.job_config, self.config)

    @patch('mash.services.deprecate.ec2_mp_job.get_image_delivery_option_id')
    @patch('mash.services.deprecate.ec2_mp_job.get_session')
    @patch('mash.services.deprecate.ec2_mp_job.start_mp_change_set')
    @patch('mash.services.deprecate.ec2_mp_job.get_image')
    def test_deprecate(
        self,
        mock_get_image,
        mock_start_change_set,
        mock_get_session,
        mock_get_delivery_option_id
    ):
        mock_get_image.return_value = {'ImageId': 'ami-123'}
        mock_get_delivery_option_id.return_value = '1234567-12345-23456-23456'
        mock_start_change_set.return_value = {'ChangeSetId': '123'}

        client = Mock()
        session = Mock()
        session.client.return_value = client
        mock_get_session.return_value = session

        self.job.run_job()

        mock_start_change_set.assert_called_once_with(
            client,
            change_set=[
                {
                    'ChangeType': 'AddDeliveryOptions',
                    'Entity': {
                        'Type': 'AmiProduct@1.0',
                        'Identifier': '123'
                    },
                    'Details': '{"new": "version"}'
                },
                {
                    'ChangeType': 'RestrictDeliveryOptions',
                    'Entity': {
                        'Type': 'AmiProduct@1.0',
                        'Identifier': '123'
                    },
                    'Details': '{"DeliveryOptionIds": ["1234567-12345-23456-23456"]}'
                }
            ]
        )

        assert self.job.status == 'success'
        assert self.job.status_msg['change_set_id'] == '123'

    @patch('mash.services.deprecate.ec2_mp_job.get_image')
    def test_deprecate_exception(
        self,
        mock_get_image,
    ):
        mock_get_image.side_effect = Exception('Failed to get image.')

        with raises(Exception):
            self.job.run_job()
