import json

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.base_service import BaseService
from mash.services.jobcreator.service import JobCreatorService


class TestJobCreatorService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None
        self.config = Mock()
        self.config.config_data = None
        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.jobcreator = JobCreatorService()
        self.jobcreator.log = Mock()
        self.jobcreator.add_account_key = 'add_account'
        self.jobcreator.accounts_file = '../data/accounts.json'
        self.jobcreator.encryption_keys_file = '../data/encryption_keys'
        self.jobcreator.service_exchange = 'jobcreator'
        self.jobcreator.listener_queue = 'listener'
        self.jobcreator.job_document_key = 'job_document'
        self.jobcreator.services = [
            'obs', 'uploader', 'testing', 'replication',
            'publisher', 'deprecation', 'pint'
        ]

    @patch.object(JobCreatorService, 'bind_queue')
    @patch.object(JobCreatorService, 'set_logfile')
    @patch.object(JobCreatorService, 'start')
    @patch('mash.services.jobcreator.service.JobCreatorConfig')
    def test_job_creator_post_init(
        self, mock_jobcreator_config, mock_start, mock_set_logfile,
        mock_bind_queue
    ):
        mock_jobcreator_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with('jobcreator')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )

        mock_bind_queue.assert_called_once_with(
            'jobcreator', 'add_account', 'listener'
        )
        mock_start.assert_called_once_with()

    @patch('mash.services.jobcreator.ec2_job.random')
    @patch('mash.services.jobcreator.base_job.uuid')
    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message(
            self, mock_publish, mock_uuid, mock_random
    ):
        message = MagicMock()

        uuid_val = '12345678-1234-1234-1234-123456789012'
        mock_uuid.uuid4.return_value = uuid_val

        mock_random.choice.side_effect = [
            'us-gov-west-1', 'ap-northeast-1'
        ]

        with open('../data/job.json', 'r') as accounts_file:
            message.body = json.dumps(json.load(accounts_file))

        self.jobcreator._handle_service_message(message)

        mock_publish.assert_has_calls([
            call(
                'credentials', 'job_document',
                '{"credentials_job": {"provider": "ec2", '
                '"last_service": "pint", '
                '"provider_accounts": ["test-aws-gov", "test-aws"], '
                '"requesting_user": "user1", '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'obs', 'job_document',
                '{"obs_job": {"image": "test_image_oem", '
                '"project": "Cloud:Tools", '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now", '
                '"conditions": [{"package": ["name", "and", "constraints"]}, '
                '{"image": "version"}]}}'
            ),
            call(
                'uploader', 'job_document',
                '{"uploader_job": {"cloud_image_name": "new_image_123", '
                '"provider": "ec2", "image_description": "New Image #123", '
                '"target_regions": {"us-gov-west-1": {"account": '
                '"test-aws-gov", "helper_image": "ami-c2b5d7e1"}, '
                '"ap-northeast-1": {"account": "test-aws", '
                '"helper_image": "ami-383c1956"}}, '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'testing', 'job_document',
                '{"testing_job": {"provider": "ec2", "tests": ["test_stuff"], '
                '"test_regions": {"us-gov-west-1": "test-aws-gov", '
                '"ap-northeast-1": "test-aws"}, "distro": "sles", '
                '"instance_type": "t2.micro", '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'replication', 'job_document',
                '{"replication_job": {"image_description": "New Image #123", '
                '"provider": "ec2", "replication_source_regions": {'
                '"us-gov-west-1": {"account": "test-aws-gov", '
                '"target_regions": ["us-gov-west-1"]}, "ap-northeast-1": '
                '{"account": "test-aws", "target_regions": ["ap-northeast-1", '
                '"ap-northeast-2"]}}, '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'publisher', 'job_document',
                '{"publisher_job": {"provider": "ec2", "allow_copy": false, '
                '"share_with": "all", "publish_regions": ['
                '{"account": "test-aws-gov", "target_regions": '
                '["us-gov-west-1"], "helper_image": "ami-c2b5d7e1"}, '
                '{"account": "test-aws", "target_regions": '
                '["ap-northeast-1", "ap-northeast-2"], "helper_image": '
                '"ami-383c1956"}], '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'deprecation', 'job_document',
                '{"deprecation_job": {"provider": "ec2", '
                '"old_cloud_image_name": "old_new_image_123", '
                '"deprecation_regions": [{"account": "test-aws-gov", '
                '"target_regions": ["us-gov-west-1"], '
                '"helper_image": "ami-c2b5d7e1"}, {"account": "test-aws", '
                '"target_regions": ["ap-northeast-1", "ap-northeast-2"], '
                '"helper_image": "ami-383c1956"}], '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            ),
            call(
                'pint', 'job_document',
                '{"pint_job": {"provider": "ec2", "cloud_image_name": '
                '"new_image_123", "old_cloud_image_name": '
                '"old_new_image_123", '
                '"id": "12345678-1234-1234-1234-123456789012", '
                '"utctime": "now"}}'
            )
        ])

    def test_jobcreator_handle_invalid_service_message(self):
        message = MagicMock()
        message.body = 'invalid message'

        self.jobcreator._handle_service_message(message)
        self.jobcreator.log.error.assert_called_once_with(
            'Invalid message received: '
            'Expecting value: line 1 column 1 (char 0).'
        )

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_publish_delete_job_message(self, mock_publish):
        message = MagicMock()
        message.body = '{"job_delete": "1"}'
        self.jobcreator._handle_service_message(message)
        mock_publish.assert_has_calls([
            call('obs', 'job_document', '{"obs_job_delete": "1"}'),
            call(
                'credentials', 'job_document',
                '{"credentials_job_delete": "1"}'
            )
        ])

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start(self, mock_stop, mock_consume_queue):
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.channel.start_consuming.assert_called_once_with()

        mock_consume_queue.assert_has_calls([
            call(self.jobcreator._handle_service_message),
            call(
                self.jobcreator._handle_listener_message,
                queue_name='listener'
            )
        ])
        mock_stop.assert_called_once_with()

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start_exception(self, mock_stop, mock_consume_queue):
        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()

        self.channel.start_consuming.side_effect = Exception(
            'Cannot start job creator service.'
        )

        with raises(Exception) as error:
            self.jobcreator.start()

        assert 'Cannot start job creator service.' == str(error.value)

    @patch.object(JobCreatorService, 'close_connection')
    def test_jobcreator_stop(self, mock_close_connection):
        self.jobcreator.channel = self.channel

        self.jobcreator.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
