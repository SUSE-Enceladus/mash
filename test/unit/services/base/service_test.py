import io
import jwt

from unittest.mock import patch
from unittest.mock import call
from unittest.mock import MagicMock, Mock
from pytest import raises

from mash.services.base_service import BaseService
from mash.services.base_defaults import Defaults

from mash.mash_exceptions import (
    MashCredentialsException,
    MashRabbitConnectionException,
    MashLogSetupException
)

open_name = "builtins.open"


class TestBaseService(object):
    @patch('mash.services.base_service.os.makedirs')
    @patch.object(Defaults, 'get_job_directory')
    @patch('mash.services.base_service.Connection')
    def setup(self, mock_connection, mock_get_job_directory, mock_makedirs):
        mock_get_job_directory.return_value = '/var/lib/mash/obs_jobs/'
        self.connection = Mock()
        self.channel = Mock()
        self.msg_properties = {
            'content_type': 'application/json',
            'delivery_mode': 2
        }
        queue = Mock()
        queue.method.queue = 'queue'
        self.channel.queue.declare.return_value = queue
        self.channel.exchange.declare.return_value = queue
        self.connection.channel.return_value = self.channel
        self.connection.is_closed = True
        mock_connection.return_value = self.connection
        self.service = BaseService('localhost', 'obs')
        mock_get_job_directory.assert_called_once_with('obs')
        mock_makedirs.assert_called_once_with(
            '/var/lib/mash/obs_jobs/', exist_ok=True
        )
        self.service.log = Mock()
        mock_connection.side_effect = Exception
        with raises(MashRabbitConnectionException):
            BaseService('localhost', 'obs')
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    @patch('logging.FileHandler')
    def test_set_logfile(self, mock_logging_FileHandler):
        logfile_handler = Mock()
        mock_logging_FileHandler.return_value = logfile_handler

        self.service.set_logfile('/some/log')
        mock_logging_FileHandler.assert_called_once_with(
            encoding='utf-8', filename='/some/log'
        )
        self.service.log.addHandler.assert_has_calls(
            [call(logfile_handler)]
        )

    @patch('logging.FileHandler')
    def test_set_logfile_raises(self, mock_logging_FileHandler):
        mock_logging_FileHandler.side_effect = Exception
        with raises(MashLogSetupException):
            self.service.set_logfile('/some/log')

    @patch('mash.services.base_service.Connection')
    def test_publish_job_result(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_job_result('exchange', 'job_id', 'message')
        self.channel.queue.declare.assert_called_once_with(
            queue='exchange.service', durable=True
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='exchange', routing_key='job_id',
            queue='exchange.service'
        )
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='exchange', mandatory=True,
            properties=self.msg_properties, routing_key='job_id'
        )

    @patch('mash.services.base_service.Connection')
    def test_publish_credentials_result(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_credentials_result('job_id', 'csp', 'message')
        self.channel.queue.declare.assert_called_once_with(
            queue='credentials.csp', durable=True
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='credentials', routing_key='job_id',
            queue='credentials.csp'
        )
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='credentials', mandatory=True,
            properties=self.msg_properties, routing_key='job_id'
        )

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback)
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='obs.service'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()

    def test_persist_job_config(self):
        self.service.job_directory = 'tmp-dir/'

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.service.persist_job_config({'id': '1'})
            file_handle = mock_open.return_value.__enter__.return_value
            # Dict is mutable, mock compares the final value of Dict
            # not the initial value that was passed in.
            file_handle.write.assert_called_with(
                u'{"id": "1", "job_file": "tmp-dir/job-1.json"}'
            )

    @patch('mash.services.base_service.json.load')
    @patch('mash.services.base_service.os.listdir')
    def test_restart_jobs(self, mock_os_listdir, mock_json_load):
        self.service.job_directory = 'tmp-dir'
        mock_os_listdir.return_value = ['job-123.json']
        mock_json_load.return_value = {'id': '1'}

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            mock_callback = Mock()
            self.service.restart_jobs(mock_callback)

            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.call_count == 1

        mock_callback.assert_called_once_with({'id': '1'})

    @patch.object(BaseService, 'bind_queue')
    def test_bind_listener_queue(self, mock_bind_queue):
        self.service.bind_listener_queue('1')
        mock_bind_queue.assert_called_once_with(
            'obs', '1', 'listener'
        )

    def test_unbind_queue(self):
        self.service.unbind_queue(
            'service', 'testing', '1'
        )
        self.service.channel.queue.unbind.assert_called_once_with(
            queue='service', exchange='testing', routing_key='1'
        )

    def test_get_credentials_request(self):
        self.service.jwt_algorithm = 'HS256'
        self.service.secret = 'super.secret'
        self.service_exchange = 'obs'
        token = self.service.get_credential_request('1')

        payload = jwt.decode(
            token, 'super.secret', algorithm='HS256',
            issuer='obs', audience='credentials'
        )

        assert payload['id'] == '1'
        assert payload['sub'] == 'credentials_request'

    @patch('mash.services.base_service.jwt')
    def test_decode_credentials(self, mock_jwt):
        self.service.jwt_algorithm = 'HS256'
        self.service.secret = 'super.secret'
        self.service_exchange = 'obs'

        message = Mock()
        mock_jwt.decode.return_value = {
            "credentials": {
                "test-aws": {
                    "access_key_id": "123456",
                    "secret_access_key": "654321",
                    "ssh_key_name": "key-123",
                    "ssh_private_key": "key123"
                },
                "test-aws-cn": {
                    "access_key_id": "654321",
                    "secret_access_key": "123456",
                    "ssh_key_name": "key-321",
                    "ssh_private_key": "key321"
                }
            }
        }

        accounts = self.service.decode_credentials(message, 'ec2')

        mock_jwt.decode.assert_called_once_with(
            message, 'super.secret', algorithm='HS256',
            issuer='credentials', audience='obs'
        )

        assert len(accounts) == 2

        # Invalid payload
        mock_jwt.decode.return_value = {}

        msg = 'Credentials not found in payload.'
        with raises(MashCredentialsException) as e:
            self.service.decode_credentials(message, 'ec2')
        assert msg == str(e.value)
        # Invalid payload

        # Credential exception
        mock_jwt.decode.side_effect = Exception('Token is broken!')

        msg = 'Invalid credentials response token: Token is broken!'
        with raises(MashCredentialsException) as e:
            self.service.decode_credentials(message, 'ec2')
        assert msg == str(e.value)
        # Credential exception

    @patch.object(BaseService, 'get_credential_request')
    @patch.object(BaseService, '_publish')
    def test_publish_credentials_request(
        self, mock_publish, mock_get_credential_request
    ):
        token = Mock()
        mock_get_credential_request.return_value = token

        self.service.service_exchange = 'obs'
        self.service.publish_credentials_request('1')

        mock_publish.assert_called_once_with(
            'credentials', 'request.obs', token
        )
