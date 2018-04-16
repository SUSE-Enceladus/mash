import io
import jwt

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.base_service import BaseService
from mash.services.credentials.service import CredentialsService


class TestCredentialsService(object):
    @patch.object(BaseService, '__init__')
    def setup(self, mock_BaseService):
        mock_BaseService.return_value = None

        self.config = Mock()
        self.config.config_data = None

        self.service = CredentialsService()
        self.service.add_account_key = 'add_account'
        self.service.service_exchange = 'credentials'
        self.service.service_queue = 'service'
        self.service.listener_queue = 'listener'
        self.service.job_document_key = 'job_document'
        self.service.credentials_queue = 'credentials'
        self.service.credentials_directory = '/var/lib/mash/credentials/'

        self.service.channel = Mock()
        self.service.channel.basic_ack.return_value = None
        self.service.channel.is_open = True
        self.service.jobs = {}
        self.service.log = Mock()

    @patch.object(CredentialsService, 'set_logfile')
    @patch('mash.services.credentials.service.CredentialsConfig')
    @patch.object(CredentialsService, 'start')
    @patch.object(CredentialsService, '_bind_credential_request_keys')
    @patch.object(CredentialsService, 'restart_jobs')
    def test_post_init(
        self, mock_restart_jobs, mock_bind_cred_req_keys, mock_start,
        mock_credentials_config, mock_set_logfile
    ):
        mock_credentials_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/credentials_service.log'

        self.service.post_init()

        self.config.get_log_file.assert_called_once_with('credentials')
        self.config.get_service_names.assert_called_once_with(
            credentials_required=True
        )
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/credentials_service.log'
        )

        mock_bind_cred_req_keys.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.service._add_job)
        mock_start.assert_called_once_with()

    @patch.object(CredentialsService, 'persist_job_config')
    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_add_job(
        self, mock_send_control_response, mock_persist_job_config
    ):
        mock_persist_job_config.return_value = 'temp-config.json'
        self.service._add_job({'id': '1', 'provider': 'ec2'})

        mock_persist_job_config.assert_called_once_with(
            {'id': '1', 'provider': 'ec2', 'job_file': 'temp-config.json'}
        )
        mock_send_control_response.assert_called_once_with(
            'Job queued, awaiting credentials requests.',
            job_id='1'
        )

    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_add_job_exists(self, mock_send_control_response):
        job = {'id': '1', 'provider': 'ec2'}

        self.service.jobs['1'] = job
        self.service._add_job({'id': '1', 'provider': 'ec2'})

        mock_send_control_response.assert_called_once_with(
            'Job already queued.', success=False, job_id='1'
        )

    @patch.object(CredentialsService, 'bind_queue')
    def test_credentials_bind_credential_request_keys(self, mock_bind_queue):
        self.service.services = [
            'replication', 'deprecation', 'uploader',
            'testing', 'publisher', 'pint'
        ]
        self.service._bind_credential_request_keys()

        mock_bind_queue.assert_has_calls([
            call('credentials', 'request.replication', 'request'),
            call('credentials', 'request.deprecation', 'request'),
            call('credentials', 'request.uploader', 'request'),
            call('credentials', 'request.testing', 'request'),
            call('credentials', 'request.publisher', 'request'),
            call('credentials', 'request.pint', 'request')
        ])

    @patch('mash.services.credentials.service.os.path')
    def test_check_credentials_exist(self, mock_path):
        mock_path.exists.return_value = True

        assert self.service._check_credentials_exist(
            'account1', 'ec2', 'user1'
        )

    @patch.object(CredentialsService, 'remove_file')
    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_delete_job(
        self, mock_send_control_response, mock_remove_file
    ):
        job = {'id': '1', 'provider': 'ec2', 'job_file': 'temp-config.json'}

        self.service.jobs['1'] = job
        self.service._delete_job('1')

        mock_send_control_response.assert_called_once_with(
            'Deleting job.', job_id='1'
        )
        mock_remove_file.assert_called_once_with('temp-config.json')

    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_delete_invalid_job(self, mock_send_control_response):
        self.service._delete_job('1')

        mock_send_control_response.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            success=False, job_id='1'
        )

    def test_get_encrypted_credentials(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = 'secret_stuff'

            result = self.service._get_encrypted_credentials(
                'account1', 'ec2', 'user1'
            )

        assert result == 'secret_stuff'

    @patch.object(CredentialsService, '_store_encrypted_credentials')
    @patch.object(CredentialsService, '_send_control_response')
    def test_handle_account_request(
        self, mock_send_control_response, mock_store_encrypted_credentials
    ):
        message = MagicMock()
        message.body = 'invalid'

        self.service._handle_account_request(message)
        mock_send_control_response.assert_called_once_with(
            'Invalid account request: Expecting value: line 1 column 1 '
            '(char 0).', success=False
        )
        message.ack.assert_called_once_with()
        message.reset_mock()

        message.body = '''{
            "account_name": "test-aws",
            "credentials": "encrypted_creds",
            "provider": "ec2",
            "requesting_user": "user1"
        }'''
        self.service._handle_account_request(message)
        mock_store_encrypted_credentials.assert_called_once_with(
            'test-aws', 'encrypted_creds', 'ec2', 'user1'
        )
        message.ack.assert_called_once_with()

    @patch.object(CredentialsService, '_add_job')
    def test_credentials_handle_job_docs_add(self, mock_add_job):
        message = Mock()
        message.body = '{"credentials_job": {"id": "1"}}'

        self.service._handle_job_documents(message)

        message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with({'id': '1'})

    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_handle_job_docs_format(
        self, mock_send_control_response
    ):
        message = Mock()
        message.body = 'Invalid format.'
        self.service._handle_job_documents(message)

        message.ack.assert_called_once_with()
        mock_send_control_response.assert_called_once_with(
            'Error adding job: Expecting value:'
            ' line 1 column 1 (char 0).', success=False
        )

    @patch.object(CredentialsService, '_delete_job')
    def test_credentials_handle_job_docs_delete(self, mock_delete_job):
        message = Mock()
        message.body = '{"credentials_job_delete": "1"}'

        self.service._handle_job_documents(message)

        message.ack.assert_called_once_with()
        mock_delete_job.assert_called_once_with('1')

    @patch('mash.services.credentials.service.jwt')
    @patch.object(CredentialsService, '_send_credential_response')
    def test_handle_credentials_request(
        self, mock_send_credential_response, mock_jwt
    ):
        message = MagicMock()
        message.method['routing_key'] = 'request.testing'
        message.body = '{"jwt_token": "test"}'

        self.service.jwt_secret = 'secret'
        self.service.jwt_algorithm = 'HS256'

        mock_jwt.decode.return_value = 'payload'

        self.service._handle_credential_request(message)

        mock_send_credential_response.assert_called_once_with('payload')
        message.ack.assert_called_once_with()

    @patch('mash.services.credentials.service.jwt')
    @patch.object(CredentialsService, '_send_control_response')
    def test_handle_credentials_request_exception(
        self, mock_send_control_response, mock_jwt
    ):
        message = MagicMock()
        message.method = {'routing_key': 'request.testing'}
        message.body = '{"jwt_token": "test"}'

        self.service.jwt_secret = 'secret'
        self.service.jwt_algorithm = 'HS256'

        mock_jwt.decode.side_effect = Exception('Invalid token!')

        self.service._handle_credential_request(message)

        mock_send_control_response.assert_called_once_with(
            'Invalid token request received from testing service: '
            'Invalid token!', success=False
        )
        message.ack.assert_called_once_with()

    @patch.object(CredentialsService, 'encrypt_credentials')
    @patch('mash.services.credentials.service.os.makedirs')
    @patch('mash.services.credentials.service.os.path.isdir')
    def test_store_encrypted_credentials(
        self, mock_isdir, mock_makedirs, mock_encrypt_creds
    ):
        mock_isdir.return_value = False

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service._store_encrypted_credentials(
                'account1', 'encrypted_secrets', 'ec2', 'user1'
            )
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_once_with('encrypted_secrets')

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.side_effect = Exception('Cannot write file')

            self.service._store_encrypted_credentials(
                'account1', 'encrypted_secrets', 'ec2', 'user1'
            )
            self.service.log.error.assert_called_once_with(
                'Unable to store credentials: Cannot write file.'
            )

    @patch.object(CredentialsService, '_retrieve_credentials')
    def test_get_credentials_response(self, mock_retrieve_credentials):
        self.service.jwt_algorithm = 'HS256'
        self.service.jwt_secret = 'super.secret'

        mock_retrieve_credentials.return_value = 'test'

        token = self.service._get_credentials_response('1', 'testing')

        payload = jwt.decode(
            token, 'super.secret', algorithm='HS256',
            issuer='credentials', audience='testing'
        )

        mock_retrieve_credentials.assert_called_once_with('1')
        assert payload['id'] == '1'
        assert payload['sub'] == 'credentials_response'

    @patch.object(CredentialsService, 'bind_queue')
    @patch.object(CredentialsService, '_publish')
    def test_publish_credentials_response(self, mock_publish, mock_bind_queue):
        self.service.credentials_response_key = 'response'
        self.service._publish_credentials_response('response', 'testing')

        mock_bind_queue.assert_called_once_with(
            'testing', 'response', 'credentials'
        )
        mock_publish.assert_called_once_with(
            'testing', 'response', 'response'
        )

    @patch.object(CredentialsService, '_delete_job')
    @patch.object(CredentialsService, '_get_credentials_response')
    @patch.object(CredentialsService, '_publish_credentials_response')
    def test_send_credential_response(
        self, mock_publish_credentials_response, mock_get_cred_response,
        mock_delete_job
    ):
        job = {'id': '1', 'last_service': 'pint', 'utctime': 'now'}
        self.service.jobs = {'1': job}

        mock_get_cred_response.return_value = b'response'

        self.service._send_credential_response({'id': '1', 'iss': 'pint'})
        mock_get_cred_response.assert_called_once_with('1', 'pint')
        mock_publish_credentials_response.assert_called_once_with(
            '{"jwt_token": "response"}', 'pint'
        )
        mock_delete_job.assert_called_once_with('1')

    @patch.object(CredentialsService, '_send_control_response')
    def test_send_credential_response_invalid(
        self, mock_send_control_response
    ):
        self.service._send_credential_response({'id': '1', 'iss': 'pint'})
        mock_send_control_response.assert_called_once_with(
            'Credentials job 1 does not exist.', success=False
        )

    def test_send_control_response_local(self):
        self.service._send_control_response(
            'message', False, '4711'
        )
        self.service.log.error.assert_called_once_with(
            'message',
            extra={'job_id': '4711'}
        )

    def test_send_control_response_public(self):
        self.service._send_control_response('message')
        self.service.log.info.assert_called_once_with(
            'message',
            extra={}
        )

    def test_retrieve_credentials(self):
        self.service.jobs = {
            '1': {
                'id': '1',
                'provider': 'ec2',
                'provider_accounts': ['test-aws'],
                'requesting_user': 'user1',
                'last_service': 'pint'
            }
        }
        credentials = self.service._retrieve_credentials('1')

        assert credentials['test-aws']['access_key_id'] is None
        assert credentials['test-aws']['secret_access_key'] is None
        assert credentials['test-aws']['ssh_key_name'] is None
        assert credentials['test-aws']['ssh_private_key'] is None

    def test_retrieve_testing_credentials(self):
        # TODO: Remove when credentials storage implemented.
        self.service.jobs = {
            '1': {
                'id': '1',
                'provider': 'ec2',
                'provider_accounts': ['test-aws'],
                'requesting_user': 'user1',
                'last_service': 'pint',
                'test_credentials': {
                    'access_key_id': '123456',
                    'secret_access_key': '654321',
                    'ssh_key_name': 'my-key',
                    'ssh_private_key': 'my-key.pem'
                }
            }
        }
        credentials = self.service._retrieve_credentials('1')

        assert credentials['test-aws']['access_key_id'] == '123456'
        assert credentials['test-aws']['secret_access_key'] == '654321'
        assert credentials['test-aws']['ssh_key_name'] == 'my-key'
        assert credentials['test-aws']['ssh_private_key'] == 'my-key.pem'

    @patch.object(CredentialsService, 'consume_credentials_queue')
    @patch.object(CredentialsService, 'consume_queue')
    @patch.object(CredentialsService, 'stop')
    def test_credentials_start(
        self, mock_stop, mock_consume_queue, mock_consume_creds_queue
    ):
        self.service.start()

        self.service.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.has_calls([
            call(self.service._handle_job_documents),
            call(self.service._handle_account_request, queue_name='listener')
        ])
        mock_consume_creds_queue.assert_called_once_with(
            self.service._handle_credential_request, queue_name='request'
        )
        mock_stop.assert_called_once_with()

    @patch.object(CredentialsService, 'consume_credentials_queue')
    @patch.object(CredentialsService, 'consume_queue')
    @patch.object(CredentialsService, 'stop')
    def test_credentials_start_exception(
        self, mock_stop, mock_consume_queue, mock_consume_creds_queue
    ):
        self.service.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.service.start()

        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()
        self.service.channel.start_consuming.side_effect = Exception(
            'Cannot start scheduler.'
        )

        with raises(Exception) as error:
            self.service.start()

        assert 'Cannot start scheduler.' == str(error.value)

    @patch.object(CredentialsService, 'close_connection')
    def test_credentials_stop(self, mock_close_connection):
        self.service.stop()
        mock_close_connection.assert_called_once_with()
        self.service.channel.stop_consuming.assert_called_once_with()
