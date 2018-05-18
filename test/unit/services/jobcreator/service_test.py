import io

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.base_service import BaseService
from mash.services.jobcreator.accounts import accounts_template
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

    @patch.object(JobCreatorService, '_write_accounts_to_file')
    @patch('mash.services.jobcreator.service.os')
    @patch.object(JobCreatorService, 'set_logfile')
    @patch.object(JobCreatorService, 'start')
    @patch('mash.services.jobcreator.service.JobCreatorConfig')
    @patch.object(JobCreatorService, 'bind_queue')
    def test_job_creator_post_init(
        self, mock_bind_queue, mock_jobcreator_config,
        mock_start, mock_set_logfile, mock_os, mock_write_accounts_to_file
    ):
        mock_os.path.exists.return_value = False
        mock_jobcreator_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with('jobcreator')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )

        mock_write_accounts_to_file.assert_called_once_with(
            accounts_template
        )

        mock_bind_queue.assert_has_calls([
            call('jobcreator', 'add_account', 'listener'),
        ])
        mock_start.assert_called_once_with()

    @patch.object(JobCreatorService, 'encrypt_credentials')
    @patch.object(JobCreatorService, '_write_accounts_to_file')
    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_add_account(
            self, mock_publish, mock_write_accounts_to_file,
            mock_encrypt_creds
    ):
        mock_encrypt_creds.return_value = 'encrypted_string'

        # Invalid json message
        self.jobcreator.add_account({"invalid": "message"})
        self.jobcreator.log.info.reset_mock()

        # New account
        self.jobcreator.add_account({
            "account_name": "test123",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "group1",
            "partition": "aws",
            "provider": "ec2",
            "requesting_user": "user1"
        })

        mock_write_accounts_to_file.call_count = 1
        mock_encrypt_creds.assert_called_once_with(
            '{"access_key_id": "123456", "secret_access_key": "654321"}'
        )
        mock_publish.assert_called_once_with(
            'credentials', 'add_account',
            '{"account_name": "test123", '
            '"credentials": "encrypted_string", '
            '"group": "group1", '
            '"partition": "aws", '
            '"provider": "ec2", '
            '"requesting_user": "user1"}'
        )

        # Existing account
        self.jobcreator.add_account({
            "account_name": "test-aws",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "group1",
            "partition": "aws",
            "provider": "ec2",
            "requesting_user": "user1"
        })

        self.jobcreator.log.warning.assert_called_once_with(
            'Failed to add account for user1 with the name test-aws. Account is '
            'owned by a different user.'
        )

        self.jobcreator.log.warning.reset_mock()

        # Existing group not owned by user
        self.jobcreator.add_account({
            "account_name": "test123",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "test",
            "partition": "aws",
            "provider": "ec2",
            "requesting_user": "user1"
        })

        self.jobcreator.log.warning.assert_called_once_with(
            'Unable to add account to group test for user1. '
            'Group owned by a different user.'
        )

        # Existing group owned by user
        self.jobcreator.add_account({
            "account_name": "test123",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "test1",
            "partition": "aws",
            "provider": "ec2",
            "requesting_user": "user1"
        })

    @patch.object(JobCreatorService, 'add_account')
    def test_jobcreator_handle_listener_message(
            self, mock_add_account
    ):
        message = MagicMock()

        # Test add account message
        message.method = {'routing_key': 'add_account'}
        message.body = '''{
                      "account_name": "test-aws",
                      "credentials": {
                        "access_key_id": "123456",
                        "secret_access_key": "654321"
                      },
                      "group": "group1",
                      "partition": "aws",
                      "provider": "ec2",
                      "requesting_user": "user1"
                }'''

        self.jobcreator._handle_listener_message(message)

        mock_add_account.assert_called_once_with({
            "account_name": "test-aws",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "group1",
            "partition": "aws",
            "provider": "ec2",
            "requesting_user": "user1"
        })
        message.ack.assert_called_once_with()
        message.ack.reset_mock()

        # Unknown routing key
        message.method['routing_key'] = 'add_group'
        self.jobcreator._handle_listener_message(message)

        self.jobcreator.log.warning.assert_called_once_with(
            'Received unknown message type: add_group. '
            'Message: {0}'.format(message.body)
        )

    def test_jobcreator_handle_invalid_listener_message(self):
        message = MagicMock()
        message.body = 'invalid message'

        self.jobcreator._handle_listener_message(message)
        self.jobcreator.log.warning.assert_called_once_with(
            'Invalid message received: invalid message.'
        )

        message.ack.assert_called_once_with()

    def test_jobcreator_write_accounts_to_file(self):
        accounts = {'test': 'accounts'}

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.jobcreator._write_accounts_to_file(accounts)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_with(
                u'{\n    "test": "accounts"\n}'
            )

    @patch.object(JobCreatorService, '_publish')
    def test_publish_delete_job_message(self, mock_publish):
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
