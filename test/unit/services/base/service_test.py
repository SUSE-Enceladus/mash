import io
import json
import jwt

from amqpstorm import AMQPError
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import MagicMock, Mock
from pytest import raises

from mash.services.base_service import BaseService
from mash.services.base_defaults import Defaults

from mash.mash_exceptions import (
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
            queue='exchange.listener', durable=True
        )
        self.channel.queue.bind.assert_called_once_with(
            exchange='exchange', routing_key='job_id',
            queue='exchange.listener'
        )
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='exchange', mandatory=True,
            properties=self.msg_properties, routing_key='job_id'
        )

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback)
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='obs.service'
        )

    def test_consume_credentials_queue(self):
        callback = Mock()
        config = Mock()
        config.get_jwt_secret.return_value = 'a-secret'
        config.get_jwt_algorithm.return_value = 'HS256'
        self.service.config = config

        self.service.consume_credentials_queue(callback)
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='obs.credentials'
        )

        assert self.service.jwt_secret == 'a-secret'
        assert self.service.jwt_algorithm == 'HS256'

    @patch.object(BaseService, 'bind_queue')
    def test_bind_credentials_queue(self, mock_bind_queue):
        self.service.bind_credentials_queue()

        mock_bind_queue.assert_called_once_with(
            'obs', 'response', 'credentials'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()

    def test_log_job_message(self):
        self.service.log_job_message('Test message', {'job_id': '1'})

        self.service.log.info.assert_called_once_with(
            'Test message',
            extra={'job_id': '1'}
        )

        self.service.log_job_message(
            'Test error message', {'job_id': '1'}, success=False
        )

        self.service.log.error.assert_called_once_with(
            'Test error message',
            extra={'job_id': '1'}
        )

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

    @patch('mash.services.base_service.os.remove')
    def test_remove_file(self, mock_remove):
        mock_remove.side_effect = Exception('File not found.')
        self.service.remove_file('job-test.json')
        mock_remove.assert_called_once_with('job-test.json')

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

    def test_unbind_listener_queue(self):
        self.service.unbind_listener_queue('1')
        self.service.channel.queue.unbind.assert_called_once_with(
            queue='listener', exchange='obs', routing_key='1'
        )

    def test_get_credentials_request(self):
        self.service.jwt_algorithm = 'HS256'
        self.service.jwt_secret = 'super.secret'
        self.service_exchange = 'obs'
        message = self.service.get_credential_request('1')

        token = json.loads(message)['jwt_token']
        payload = jwt.decode(
            token, 'super.secret', algorithm='HS256',
            issuer='obs', audience='credentials'
        )

        assert payload['id'] == '1'
        assert payload['sub'] == 'credentials_request'

    @patch('mash.services.base_service.jwt')
    def test_decode_credentials(self, mock_jwt):
        self.service.jwt_algorithm = 'HS256'
        self.service.jwt_secret = 'super.secret'
        self.service_exchange = 'obs'

        message = {'jwt_token': 'secret_credentials'}
        mock_jwt.decode.return_value = {
            "id": "1",
            "credentials": {
                "test-aws": {
                    "access_key_id": "123456",
                    "secret_access_key": "654321"
                },
                "test-aws-cn": {
                    "access_key_id": "654321",
                    "secret_access_key": "123456"
                }
            }
        }

        job_id, credentials = self.service.decode_credentials(message)

        mock_jwt.decode.assert_called_once_with(
            'secret_credentials', 'super.secret', algorithm='HS256',
            issuer='credentials', audience='obs'
        )

        assert len(credentials.keys()) == 2
        assert job_id == '1'

        # Missing credentials key
        mock_jwt.decode.return_value = {"id": "1"}

        job_id, credentials = self.service.decode_credentials(message)
        self.service.log.error.assert_called_once_with(
            "Invalid credentials response recieved: 'credentials'"
            " key must be in credentials message."
        )

        # Credential exception
        self.service.log.error.reset_mock()
        mock_jwt.decode.side_effect = Exception('Token is broken!')

        job_id, credentials = self.service.decode_credentials(message)
        self.service.log.error.assert_called_once_with(
            'Invalid credentials response token: Token is broken!'
        )

    @patch.object(BaseService, '_publish')
    def test_notify_invalid_config(self, mock_publish):
        self.service.notify_invalid_config('invalid')
        mock_publish.assert_called_once_with(
            'jobcreator',
            'invalid_config',
            'invalid'
        )

    @patch.object(BaseService, '_publish')
    def test_notify_invalid_config_exception(self, mock_publish):
        mock_publish.side_effect = AMQPError('Broken')
        self.service.notify_invalid_config('invalid')

        self.service.log.warning.assert_called_once_with(
            'Message not received: {0}'.format('invalid')
        )

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
