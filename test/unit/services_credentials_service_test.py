from mock import patch
from mock import Mock

from mash.services.base_service import BaseService
from mash.services.credentials.service import CredentialsService


class TestCredentialsService(object):
    @patch.object(BaseService, '__init__')
    def setup(self, mock_BaseService):
        mock_BaseService.return_value = None
        self.service = CredentialsService()
        self.service.service_exchange = 'credentials'
        self.service.channel = Mock()
        self.service.channel.is_open = True
        self.service.close_connection = Mock()
        self.service.consume_queue = Mock()
        self.service.bind_service_queue = Mock()
        self.service._bind_queue = Mock()
        self.service._publish = Mock()
        self.service.log = Mock()

    @patch.object(CredentialsService, '_control_in')
    def test_post_init(self, mock_control_in):
        self.service.post_init()
        self.service.consume_queue.assert_called_once_with(
            mock_control_in, self.service.bind_service_queue.return_value
        )
        self.service.channel.start_consuming.assert_called_once_with()
        self.service.channel.start_consuming.side_effect = Exception
        self.service.post_init()
        self.service.channel.stop_consuming.assert_called_once_with()
        self.service.close_connection.assert_called_once_with()

    def test_send_control_response_local(self):
        result = {
            'message': 'message',
            'ok': False
        }
        self.service._send_control_response(result, '4711')
        self.service.log.error.assert_called_once_with(
            'message',
            extra={'job_id': '4711'}
        )

    def test_send_control_response_public(self):
        result = {
            'message': 'message',
            'ok': True
        }
        self.service._send_control_response(result)
        self.service.log.info.assert_called_once_with(
            'message',
            extra={}
        )

    @patch.object(CredentialsService, '_create_credentials')
    @patch.object(CredentialsService, '_send_control_response')
    def test_control_in(
        self, mock_send_control_response, mock_create_credentials
    ):
        message = '{"credentials": ' + \
            '{"id": "123", "csp": "ec2", "payload": {"foo": "bar"}}}'
        channel = Mock()
        method = Mock()
        self.service._control_in(channel, method, Mock(), message)
        channel.basic_ack.assert_called_once_with(method.delivery_tag)
        mock_create_credentials.assert_called_once_with(
            {
                'credentials': {
                    'id': '123',
                    'payload': {'foo': 'bar'},
                    'csp': 'ec2'
                }
            }
        )
        message = 'foo'
        self.service._control_in(channel, method, Mock(), message)
        mock_send_control_response.assert_called_once_with(
            {
                'message':
                    'JSON:deserialize error: foo : ' +
                    'No JSON object could be decoded',
                'ok': False
            }
        )
        mock_send_control_response.reset_mock()
        message = '{"foo": "bar"}'
        self.service._control_in(channel, method, Mock(), message)
        mock_send_control_response.assert_called_once_with(
            {
                'message': "No idea what to do with: {'foo': 'bar'}",
                'ok': False
            }
        )

    @patch.object(CredentialsService, '_send_control_response')
    def test_create_credentials(self, mock_send_control_response):
        data = {
            'credentials': {
                'id': '123',
                'csp': 'ec2',
                'payload': {'foo': 'bar'}
            }
        }
        self.service._create_credentials(data)
        mock_send_control_response.assert_called_once_with(
            {
                'ok': True,
                'message': 'Credentials token created'
            }, '123'
        )
        self.service._bind_queue.assert_called_once_with(
            'credentials', 'ec2_123'
        )
        self.service._publish.assert_called_once_with(
            'credentials', 'ec2_123', '{\n    "credentials": ' +
            '"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIif' +
            'Q.dtxWM6MIcgoeMgH87tGvsNDY6cHWL6MGW4LeYvnm1JA"\n}'
        )
        mock_send_control_response.reset_mock()
        self.service._create_credentials({})
        mock_send_control_response.assert_called_once_with(
            {
                'ok': False,
                'message': 'Insufficient job information'
            }, None
        )
