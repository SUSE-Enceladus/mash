import io
import jwt
import json

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.credentials.service import CredentialsService
from mash.services.credentials.key_rotate import rotate_key
from mash.services.jobcreator.accounts import accounts_template
from mash.utils.json_format import JsonFormat


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
        self.service.encryption_keys_file = '/var/lib/mash/encryption_keys'

        self.service.channel = Mock()
        self.service.channel.basic_ack.return_value = None
        self.service.channel.is_open = True
        self.service.jobs = {}
        self.service.log = Mock()

    @patch.object(CredentialsService, '_write_accounts_to_file')
    @patch.object(CredentialsService, '_create_encryption_keys_file')
    @patch('mash.services.credentials.service.os')
    @patch.object(CredentialsService, 'set_logfile')
    @patch.object(CredentialsService, 'start')
    @patch.object(CredentialsService, '_bind_credential_request_keys')
    @patch.object(CredentialsService, 'restart_jobs')
    def test_post_init(
        self, mock_restart_jobs, mock_bind_cred_req_keys, mock_start,
        mock_set_logfile, mock_os, mock_create_keys_file,
        mock_write_accounts_to_file
    ):
        self.service.config = self.config
        mock_os.path.exists.return_value = False
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

        mock_create_keys_file.assert_called_once_with()
        mock_write_accounts_to_file.assert_called_once_with(
            accounts_template
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
        self.service._add_job({'id': '1', 'cloud': 'ec2'})

        job_config = {
            'id': '1', 'job_file': 'temp-config.json', 'cloud': 'ec2'
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

    @patch.object(CredentialsService, '_check_credentials_exist')
    @patch.object(CredentialsService, '_get_accounts_in_group')
    def test_check_job_accounts(
        self, mock_get_accounts_in_group, mock_check_credentials_exist
    ):
        mock_get_accounts_in_group.return_value = ['test-aws', 'test-aws-cn']
        mock_check_credentials_exist.return_value = True

        value = self.service._check_job_accounts(
            'ec2', [{'name': 'test-aws'}], ['test'], 'user1'
        )

        assert value

        # Account does not exist for user
        mock_check_credentials_exist.return_value = False
        value = self.service._check_job_accounts(
            'ec2', [{'name': 'test-aws'}], ['test'], 'user1'
        )

        assert not value

    @patch.object(CredentialsService, '_get_accounts_from_file')
    @patch.object(CredentialsService, '_check_job_accounts')
    @patch.object(CredentialsService, '_send_control_response')
    @patch.object(CredentialsService, '_publish')
    def test_confirm_job(
        self, mock_publish, mock_send_control_response,
        mock_check_job_accounts, mock_get_accounts_from_file
    ):
        mock_check_job_accounts.return_value = True
        mock_get_accounts_from_file.return_value = {'accounts': 'info'}

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
        mock_check_job_accounts.return_value = False
        self.service._confirm_job(doc)

        mock_send_control_response.assert_called_once_with(
            'User does not own requested accounts.', success=False
        )
        mock_publish.assert_called_once_with(
            'jobcreator', 'job_document',
            JsonFormat.json_message({"invalid_job": "123"})
        )

    @patch.object(CredentialsService, '_generate_encryption_key')
    def test_create_encryption_keys_file(self, mock_generate_encryption_key):
        mock_generate_encryption_key.return_value = '1234567890'

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service._create_encryption_keys_file()
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_with(
                u'1234567890'
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

    @patch('mash.services.credentials.service.Fernet')
    def test_generate_encryption_key(self, mock_fernet):
        mock_fernet.generate_key.return_value = b'1234567890'
        value = self.service._generate_encryption_key()

        assert value == '1234567890'

    def test_get_accounts_from_file(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '{"ec2": {"account": "info"}}'
            result = self.service._get_accounts_from_file('ec2')

        assert result['account'] == 'info'

        # Test get accounts with no cloud
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '{"ec2": {"account": "info"}}'
            result = self.service._get_accounts_from_file()

        assert result['ec2']['account'] == 'info'

    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_get_accounts_in_group(self, mock_get_accounts_from_file):
        mock_get_accounts_from_file.return_value = {
            'groups': {
                'user1': {'test': ['test-1', 'test-2']}
            }
        }
        accounts = self.service._get_accounts_in_group('test', 'ec2', 'user1')
        assert accounts == ['test-1', 'test-2']

    def test_get_encrypted_credentials(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = 'secret_stuff'

            result = self.service._get_encrypted_credentials(
                'account1', 'ec2', 'user1'
            )

        assert result == 'secret_stuff'

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

    @patch('mash.services.credentials.service.clean_old_keys')
    def test_handle_key_rotation_result(self, mock_clean_old_keys):
        # Test exception case
        event = MagicMock()
        event.exception = 'Broken!'

        self.service._handle_key_rotation_result(event)
        self.service.log.error.assert_called_once_with(
            'Key rotation did not finish successfully.'
            ' Old key will remain in key file.'
        )

        # Test success
        event.exception = None

        self.service._handle_key_rotation_result(event)
        mock_clean_old_keys.assert_called_once_with(
            '/var/lib/mash/encryption_keys',
            self.service._send_control_response
        )
        self.service.log.info.assert_called_once_with(
            'Key rotation finished.'
        )

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
            self.service.log.info.assert_called_once_with(
                'Storing credentials for account: '
                'account1, cloud: ec2, user: user1.'
            )

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

    @patch.object(CredentialsService, '_get_credentials_response')
    @patch.object(CredentialsService, '_publish_credentials_response')
    def test_send_credential_response(
        self, mock_publish_credentials_response, mock_get_cred_response
    ):
        job = {'id': '1', 'last_service': 'pint', 'utctime': 'now'}
        self.service.jobs = {'1': job}

        mock_get_cred_response.return_value = b'response'

        self.service._send_credential_response({'id': '1', 'iss': 'pint'})
        mock_get_cred_response.assert_called_once_with('1', 'pint')
        self.service.log.info.assert_called_once_with(
            'Received credentials request from pint for job: 1.'
        )
        mock_publish_credentials_response.assert_called_once_with(
            JsonFormat.json_message({"jwt_token": "response"}), 'pint'
        )

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

    @patch.object(CredentialsService, '_get_encrypted_credentials')
    def test_retrieve_credentials(self, mock_get_encrypt_creds):
        mock_get_encrypt_creds.return_value = 'encrypted_string'
        self.service.jobs = {
            '1': {
                'id': '1',
                'cloud': 'ec2',
                'cloud_accounts': ['test-aws'],
                'requesting_user': 'user1',
                'last_service': 'pint'
            }
        }
        credentials = self.service._retrieve_credentials('1')

        assert credentials['test-aws'] == 'encrypted_string'

    def test_credentials_start_rotation_job(self):
        scheduler = Mock()
        self.service.scheduler = scheduler

        self.service._start_rotation_job()

        self.service.scheduler.add_job.assert_called_once_with(
            rotate_key,
            'cron',
            args=(
                '/var/lib/mash/credentials/',
                '/var/lib/mash/encryption_keys',
                self.service._send_control_response
            ),
            day='1st sat,3rd sat',
            hour='0',
            minute='0'
        )

    def test_credentials_write_accounts_to_file(self):
        accounts = {'test': 'accounts'}

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service._write_accounts_to_file(accounts)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_with(
                u'{\n    "test": "accounts"\n}'
            )

    @patch.object(CredentialsService, '_store_encrypted_credentials')
    @patch.object(CredentialsService, '_write_accounts_to_file')
    @patch.object(CredentialsService, 'encrypt_credentials')
    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_credentials_add_account_ec2(
        self, mock_get_acnts_from_file, mock_encrypt_creds,
        mock_write_accounts_to_file, mock_store_encrypted_creds
    ):
        message = {
            'account_name': 'acnt123',
            'credentials': {'creds': 'data'},
            'partition': 'aws',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'group': 'group123'
        }

        with open(self.service.accounts_file) as f:
            accounts = json.load(f)
        mock_get_acnts_from_file.return_value = accounts
        mock_encrypt_creds.return_value = 'encryptedcreds'

        self.service.add_account(message)

        self.service._write_accounts_to_file.assert_called_once_with(accounts)
        self.service._store_encrypted_credentials.assert_called_once_with(
            'acnt123', 'encryptedcreds', 'ec2', 'user1'
        )

        assert accounts['ec2']['accounts']['user1']['acnt123'] == \
            {'additional_regions': None, 'partition': 'aws'}
        assert accounts['ec2']['groups']['user1']['group123'] == ['acnt123']

    @patch.object(CredentialsService, '_store_encrypted_credentials')
    @patch.object(CredentialsService, '_write_accounts_to_file')
    @patch.object(CredentialsService, 'encrypt_credentials')
    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_credentials_add_account_azure(
        self, mock_get_acnts_from_file, mock_encrypt_creds,
        mock_write_accounts_to_file, mock_store_encrypted_creds
    ):
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

        with open(self.service.accounts_file) as f:
            accounts = json.load(f)
        mock_get_acnts_from_file.return_value = accounts
        mock_encrypt_creds.return_value = 'encryptedcreds'

        self.service.add_account(message)

        self.service._write_accounts_to_file.assert_called_once_with(accounts)
        self.service._store_encrypted_credentials.assert_called_once_with(
            'test-azure', 'encryptedcreds', 'azure', 'user1'
        )

        account = accounts['azure']['accounts']['user1']['test-azure']
        assert account['region'] == 'southcentralus'
        assert account['source_container'] == 'container1'
        assert account['source_resource_group'] == 'rg_1'
        assert account['source_storage_account'] == 'sa_1'
        assert account['destination_container'] == 'container2'
        assert account['destination_resource_group'] == 'rg_2'
        assert account['destination_storage_account'] == 'sa_2'

    @patch.object(CredentialsService, '_store_encrypted_credentials')
    @patch.object(CredentialsService, '_write_accounts_to_file')
    @patch.object(CredentialsService, 'encrypt_credentials')
    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_credentials_add_account_gce(
        self, mock_get_acnts_from_file, mock_encrypt_creds,
        mock_write_accounts_to_file, mock_store_encrypted_creds
    ):
        message = {
            "account_name": "test-gce",
            "bucket": "images",
            "credentials": {"encrypted": "creds"},
            "cloud": "gce",
            "region": "us-west2",
            "requesting_user": "user1"
        }

        with open(self.service.accounts_file) as f:
            accounts = json.load(f)
        mock_get_acnts_from_file.return_value = accounts
        mock_encrypt_creds.return_value = 'encryptedcreds'

        self.service.add_account(message)

        self.service._write_accounts_to_file.assert_called_once_with(accounts)
        self.service._store_encrypted_credentials.assert_called_once_with(
            'test-gce', 'encryptedcreds', 'gce', 'user1'
        )

        account = accounts['gce']['accounts']['user1']['test-gce']
        assert account['region'] == 'us-west2'
        assert account['bucket'] == 'images'

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
            'Invalid cloud for account: fake.'
        )

    @patch.object(CredentialsService, '_get_credentials_file_path')
    @patch('mash.services.credentials.service.os')
    @patch.object(CredentialsService, '_write_accounts_to_file')
    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_credentials_delete_account(
        self, mock_get_acnts_from_file, mock_write_accounts_to_file,
        mock_os, mock_get_cred_path
    ):
        mock_get_cred_path.return_value = \
            '/var/lib/mash/credentials/user2/ec2/test-aws'

        with open(self.service.accounts_file) as f:
            accounts = json.load(f)
        mock_get_acnts_from_file.return_value = accounts

        message = {
            "account_name": "test-aws",
            "cloud": "ec2",
            "requesting_user": "user2"
        }

        self.service.delete_account(message)

        mock_get_acnts_from_file.assert_called_once_with()
        self.service.log.info.assert_called_once_with(
            'Deleting credentials for account: '
            'test-aws, cloud: ec2, user: user2.'
        )
        mock_os.remove.assert_called_once_with(
            '/var/lib/mash/credentials/user2/ec2/test-aws'
        )
        mock_write_accounts_to_file.assert_called_once_with(
            {
                'ec2': {
                    'accounts': {
                        'user2': {
                            'test-aws-gov': {
                                'additional_regions': [
                                    {
                                        'name': 'ap-northeast-4',
                                        'helper_image': 'ami-82444aff'
                                    }
                                ],
                                'partition': 'aws-us-gov'
                            }
                        }
                    },
                    'groups': {
                        'user1': {
                            'test1': []
                        },
                        'user2': {
                            'test': ['test-aws-gov']
                        }
                    }
                },
                "azure": {
                    "groups": {},
                    "accounts": {
                        "user1": {
                            "test123": {
                                "container_name": "container1",
                                "region": "centralus",
                                "resource_group": "rg_123",
                                "storage_account": "sa_123"
                            }
                        }
                    }
                },
                "gce": {
                    "groups": {},
                    "accounts": {
                        "user1": {
                            "test123": {
                                "bucket": "images",
                                "region": "us-west2"
                            }
                        }
                    }
                }
            }
        )

    @patch.object(CredentialsService, '_remove_credentials_file')
    @patch.object(CredentialsService, '_get_accounts_from_file')
    def test_credentials_delete_account_invalid(
        self, mock_get_acnts_from_file, mock_rmv_creds_file
    ):
        with open(self.service.accounts_file) as f:
            accounts = json.load(f)
        mock_get_acnts_from_file.return_value = accounts

        message = {
            "account_name": "fake",
            "cloud": "ec2",
            "requesting_user": "user2"
        }

        self.service.delete_account(message)
        mock_rmv_creds_file.assert_called_once_with(
            'fake', 'ec2', 'user2'
        )
        self.service.log.error.assert_called_once_with(
            'Account fake does not exist for user2.'
        )

    @patch.object(CredentialsService, '_start_rotation_job')
    @patch.object(CredentialsService, 'consume_credentials_queue')
    @patch.object(CredentialsService, 'consume_queue')
    @patch.object(CredentialsService, 'stop')
    def test_credentials_start(
        self, mock_stop, mock_consume_queue, mock_consume_creds_queue,
        mock_start_rotation_job
    ):
        scheduler = Mock()
        self.service.scheduler = scheduler

        self.service.start()

        scheduler.start.assert_called_once_with()
        mock_start_rotation_job.assert_called_once_with()
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
        scheduler = Mock()
        self.service.scheduler = scheduler

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
        scheduler = Mock()
        self.service.scheduler = scheduler

        self.service.stop()
        scheduler.shutdown.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
        self.service.channel.stop_consuming.assert_called_once_with()
