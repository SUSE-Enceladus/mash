import io
import jwt
import json

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.base_defaults import Defaults
from mash.services.mash_service import MashService
from mash.services.credentials.service import CredentialsService
from mash.services.credentials.account_datastore import AccountDatastore
from mash.utils.json_format import JsonFormat
from mash.mash_exceptions import MashCredentialsException


class TestCredentialsService(object):
    @patch.object(MashService, '__init__')
    def setup(self, mock_BaseService):
        mock_BaseService.return_value = None

        self.config = Mock()
        self.config.config_data = None

        self.service = CredentialsService()
        self.service.add_account_key = 'add_account'
        self.service.delete_account_key = 'delete_account'
        self.service.service_exchange = 'credentials'
        self.service.service_queue = 'service'
        self.service.listener_queue = 'listener'
        self.service.job_document_key = 'job_document'
        self.service.credentials_queue = 'credentials'
        self.service.credentials_directory = '/var/lib/mash/credentials/'
        self.service.accounts_file = '../data/accounts.json'
        self.service.encryption_keys_file = '../data/encryption_keys'
        self.service.account_datastore = AccountDatastore(
            self.service.accounts_file, self.service.credentials_directory,
            self.service.encryption_keys_file,
            self.service._send_control_response
        )

        self.service.channel = Mock()
        self.service.channel.basic_ack.return_value = None
        self.service.channel.is_open = True
        self.service.jobs = {}
        self.service.log = Mock()

    @patch('mash.services.credentials.service.os.makedirs')
    @patch.object(Defaults, 'get_job_directory')
    @patch('mash.services.credentials.service.AccountDatastore')
    @patch.object(CredentialsService, 'set_logfile')
    @patch.object(CredentialsService, 'start')
    @patch.object(CredentialsService, '_bind_credential_request_keys')
    @patch.object(CredentialsService, 'restart_jobs')
    def test_post_init(
        self, mock_restart_jobs, mock_bind_cred_req_keys, mock_start,
        mock_set_logfile, mock_datastore, mock_get_job_directory,
        mock_makedirs
    ):
        mock_get_job_directory.return_value = '/var/lib/mash/obs_jobs/'
        self.service.config = self.config
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

        mock_get_job_directory.assert_called_once_with('credentials')
        mock_makedirs.assert_called_once_with(
            '/var/lib/mash/obs_jobs/', exist_ok=True
        )

        mock_bind_cred_req_keys.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.service._add_job)
        mock_start.assert_called_once_with()

    @patch.object(AccountDatastore, 'get_testing_accounts')
    @patch.object(CredentialsService, 'persist_job_config')
    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_add_job(
        self, mock_send_control_response, mock_persist_job_config,
        mock_get_testing_accounts
    ):
        mock_persist_job_config.return_value = 'temp-config.json'
        mock_get_testing_accounts.return_value = ['tester']

        self.service._add_job({
            'id': '1',
            'cloud': 'ec2',
            'cloud_accounts': ['test-gce'],
            'requesting_user': 'user1'
        })

        job_config = {
            'id': '1', 'job_file': 'temp-config.json', 'cloud': 'ec2',
            'cloud_accounts': ['test-gce', 'tester'],
            'requesting_user': 'user1'
        }
        mock_persist_job_config.assert_called_once_with(job_config)

        mock_send_control_response.assert_called_once_with(
            'Job queued, awaiting credentials requests.',
            job_id='1'
        )

    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_add_job_exists(self, mock_send_control_response):
        job = {'id': '1', 'cloud': 'ec2'}

        self.service.jobs['1'] = job
        self.service._add_job({'id': '1', 'cloud': 'ec2'})

        mock_send_control_response.assert_called_once_with(
            'Job already queued.', success=False, job_id='1'
        )

    @patch.object(CredentialsService, 'bind_queue')
    def test_credentials_bind_credential_request_keys(self, mock_bind_queue):
        self.service.services = [
            'replication', 'deprecation', 'uploader',
            'testing', 'publisher'
        ]
        self.service._bind_credential_request_keys()

        mock_bind_queue.assert_has_calls([
            call('credentials', 'request.replication', 'request'),
            call('credentials', 'request.deprecation', 'request'),
            call('credentials', 'request.uploader', 'request'),
            call('credentials', 'request.testing', 'request'),
            call('credentials', 'request.publisher', 'request')
        ])

    @patch.object(AccountDatastore, 'check_job_accounts')
    @patch.object(CredentialsService, '_send_control_response')
    @patch.object(CredentialsService, '_publish')
    def test_confirm_job(
        self, mock_publish, mock_send_control_response,
        mock_check_job_accounts
    ):
        mock_check_job_accounts.return_value = {'accounts': 'info'}

        doc = {
            'id': '123',
            'cloud': 'ec2',
            'cloud_accounts': [
                {
                    'name': 'test-aws-gov', 'target_regions': ['us-gov-west-1']
                }
            ],
            'cloud_groups': ['test'], 'requesting_user': 'user1'
        }
        self.service._confirm_job(doc)

        mock_publish.assert_called_once_with(
            'jobcreator', 'job_document',
            JsonFormat.json_message({
                "start_job": {
                    "accounts_info": {"accounts": "info"},
                    "id": "123"
                }
            })
        )

        # Invalid accounts
        mock_publish.reset_mock()
        mock_check_job_accounts.side_effect = MashCredentialsException(
            'missing account'
        )
        self.service._confirm_job(doc)

        mock_send_control_response.assert_called_once_with(
            'Invalid job: missing account.', success=False,
            job_id='123'
        )
        mock_publish.assert_called_once_with(
            'jobcreator', 'job_document',
            JsonFormat.json_message(
                {"error_msg": "missing account", "invalid_job": "123"}
            )
        )

    @patch.object(CredentialsService, 'remove_file')
    @patch.object(CredentialsService, '_send_control_response')
    def test_credentials_delete_job(
        self, mock_send_control_response, mock_remove_file
    ):
        job = {'id': '1', 'cloud': 'ec2', 'job_file': 'temp-config.json'}

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

    @patch.object(CredentialsService, 'add_account')
    @patch.object(CredentialsService, '_send_control_response')
    def test_handle_add_account(
        self, mock_send_control_response, mock_add_account
    ):
        message = MagicMock()
        message.body = 'invalid'
        message.method = {'routing_key': 'add_account'}

        self.service._handle_account_request(message)
        mock_send_control_response.assert_called_once_with(
            'Invalid account request: Expecting value: line 1 column 1 '
            '(char 0).', success=False
        )
        message.ack.assert_called_once_with()
        message.reset_mock()

        # Add ec2 account
        message.body = '''{
            "account_name": "test-aws",
            "credentials": "encrypted_creds",
            "cloud": "ec2",
            "requesting_user": "user1"
        }'''
        self.service._handle_account_request(message)
        mock_add_account.assert_called_once_with(
            json.loads(message.body)
        )
        message.ack.assert_called_once_with()

    @patch.object(CredentialsService, 'delete_account')
    def test_handle_delete_account(self, mock_delete_acnt):
        message = MagicMock()
        message.body = '''{
            "account_name": "test-aws",
            "cloud": "ec2",
            "requesting_user": "user1"
        }'''
        message.method = {'routing_key': 'delete_account'}

        self.service._handle_account_request(message)
        mock_delete_acnt.asser_called_once_with(
            json.dumps(json.loads(message.body), sort_keys=True)
        )

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

    @patch.object(CredentialsService, '_confirm_job')
    def test_credentials_handle_job_docs_job_check(self, mock_confirm_job):
        message = Mock()
        message.body = '{"credentials_job_check": {"id": "1"}}'

        self.service._handle_job_documents(message)

        message.ack.assert_called_once_with()
        mock_confirm_job.assert_called_once_with({'id': '1'})

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

    @patch.object(AccountDatastore, 'retrieve_credentials')
    def test_get_credentials_response(self, mock_retrieve_credentials):
        job = {
            'id': '1',
            'cloud': 'ec2',
            'job_file': 'temp-config.json',
            'cloud_accounts': ['test-aws'],
            'requesting_user': 'user1'
        }

        self.service.jobs['1'] = job
        self.service.jwt_algorithm = 'HS256'
        self.service.jwt_secret = 'super.secret'

        mock_retrieve_credentials.return_value = 'test'

        token = self.service._get_credentials_response('1', 'testing')

        payload = jwt.decode(
            token, 'super.secret', algorithm='HS256',
            issuer='credentials', audience='testing'
        )

        mock_retrieve_credentials.assert_called_once_with(
            ['test-aws'], 'ec2', 'user1'
        )
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

    @patch.object(CredentialsService, '_get_credentials_response')
    @patch.object(CredentialsService, '_publish_credentials_response')
    def test_send_credential_response(
        self, mock_publish_credentials_response, mock_get_cred_response
    ):
        job = {'id': '1', 'last_service': 'deprecation', 'utctime': 'now'}
        self.service.jobs = {'1': job}

        mock_get_cred_response.return_value = b'response'

        self.service._send_credential_response(
            {'id': '1', 'iss': 'deprecation'}
        )
        mock_get_cred_response.assert_called_once_with('1', 'deprecation')
        self.service.log.info.assert_called_once_with(
            'Received credentials request from deprecation for job: 1.'
        )
        mock_publish_credentials_response.assert_called_once_with(
            JsonFormat.json_message({"jwt_token": "response"}), 'deprecation'
        )

    @patch.object(CredentialsService, '_send_control_response')
    def test_send_credential_response_invalid(
        self, mock_send_control_response
    ):
        self.service._send_credential_response({'id': '1', 'iss': 'deprecation'})
        mock_send_control_response.assert_called_once_with(
            'Credentials job 1 does not exist.', success=False,
            job_id='1'
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

    @patch.object(AccountDatastore, 'add_account')
    def test_credentials_add_account_ec2(self, mock_add_account):
        message = {
            'account_name': 'acnt123',
            'credentials': {'creds': 'data'},
            'partition': 'aws',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'region': 'us-east-1',
            'group': 'group123'
        }

        self.service.add_account(message)
        assert mock_add_account.call_count == 1

    @patch.object(AccountDatastore, 'add_account')
    def test_credentials_add_account_azure(self, mock_add_account):
        message = {
            "account_name": "test-azure",
            "credentials": {"encrypted": "creds"},
            "cloud": "azure",
            "region": "southcentralus",
            "requesting_user": "user1",
            "source_container": "container1",
            "source_resource_group": "rg_1",
            "source_storage_account": "sa_1",
            "destination_container": "container2",
            "destination_resource_group": "rg_2",
            "destination_storage_account": "sa_2"
        }

        self.service.add_account(message)
        assert mock_add_account.call_count == 1

    @patch.object(AccountDatastore, 'add_account')
    def test_credentials_add_account_gce(self, mock_add_account):
        message = {
            'account_name': 'test-gce',
            'bucket': 'images',
            'credentials': {'encrypted': 'creds'},
            'cloud': 'gce',
            'region': 'us-west2',
            'requesting_user': 'user1'
        }

        self.service.add_account(message)
        assert mock_add_account.call_count == 1

    def test_credentials_add_account_invalid(self):
        message = {
            'account_name': 'acnt123',
            'credentials': {'creds': 'data'},
            'partition': 'aws',
            'cloud': 'fake',
            'requesting_user': 'user1',
            'group': 'group123'
        }

        self.service.add_account(message)
        self.service.log.warning.assert_called_once_with(
            'Failed to add account to database: CSP fake is not supported.'
        )

    @patch.object(AccountDatastore, 'add_account')
    def test_credentials_add_account_exception(self, mock_add_account):
        message = {
            'account_name': 'acnt123',
            'credentials': {'creds': 'data'},
            'partition': 'aws',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'region': 'us-east-1',
            'group': 'group123'
        }

        mock_add_account.side_effect = Exception('Forbidden!')

        self.service.add_account(message)
        assert mock_add_account.call_count == 1

        self.service.log.warning.assert_called_once_with(
            'Unable to add account: Forbidden!'
        )

    @patch.object(AccountDatastore, 'delete_account')
    def test_credentials_delete_account(self, mock_delete_account):
        message = {
            'account_name': 'test-aws',
            'cloud': 'ec2',
            'requesting_user': 'user2'
        }

        self.service.delete_account(message)

        mock_delete_account.assert_called_once_with(
            'user2', 'test-aws', 'ec2'
        )

    @patch.object(AccountDatastore, 'delete_account')
    def test_credentials_delete_account_exception(self, mock_delete_account):
        message = {
            'account_name': 'test-aws',
            'cloud': 'ec2',
            'requesting_user': 'user2'
        }

        mock_delete_account.side_effect = Exception('Forbidden!')

        self.service.delete_account(message)

        mock_delete_account.assert_called_once_with(
            'user2', 'test-aws', 'ec2'
        )

        self.service.log.warning.assert_called_once_with(
            'Unable to delete account: Forbidden!'
        )

    @patch('mash.services.credentials.service.os.remove')
    def test_remove_file(self, mock_remove):
        mock_remove.side_effect = Exception('File not found.')
        self.service.remove_file('job-test.json')
        mock_remove.assert_called_once_with('job-test.json')

    def test_persist_job_config(self):
        self.service.job_directory = 'tmp-dir/'

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service.persist_job_config({'id': '1'})
            file_handle = mock_open.return_value.__enter__.return_value
            # Dict is mutable, mock compares the final value of Dict
            # not the initial value that was passed in.
            file_handle.write.assert_called_with(
                JsonFormat.json_message({
                    "id": "1",
                    "job_file": "tmp-dir/job-1.json"
                })
            )

    @patch('mash.services.credentials.service.json.load')
    @patch('mash.services.credentials.service.os.listdir')
    def test_restart_jobs(self, mock_os_listdir, mock_json_load):
        self.service.job_directory = 'tmp-dir'
        mock_os_listdir.return_value = ['job-123.json']
        mock_json_load.return_value = {'id': '1'}

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            mock_callback = Mock()
            self.service.restart_jobs(mock_callback)

            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.call_count == 1

        mock_callback.assert_called_once_with({'id': '1'})

    @patch.object(CredentialsService, 'consume_queue')
    @patch.object(CredentialsService, 'close_connection')
    def test_credentials_start(
        self, mock_close_connection, mock_consume_queue
    ):
        self.service.start()

        self.service.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.has_calls([
            call(self.service._handle_job_documents),
            call(self.service._handle_account_request, queue_name='listener'),
            call(self.service._handle_credential_request, queue_name='request')
        ])
        mock_close_connection.assert_called_once_with()

    @patch.object(AccountDatastore, 'shutdown')
    @patch.object(CredentialsService, 'consume_queue')
    @patch.object(CredentialsService, 'close_connection')
    def test_credentials_start_exception(
        self, mock_close_connection, mock_consume_queue,
        mock_datastore_shutdown
    ):
        self.service.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.service.start()

        mock_close_connection.assert_called_once_with()
        mock_datastore_shutdown.assert_called_once_with()
        mock_close_connection.reset_mock()
        self.service.channel.start_consuming.side_effect = Exception(
            'Cannot start.'
        )

        with raises(Exception) as error:
            self.service.start()

        assert 'Cannot start.' == str(error.value)
