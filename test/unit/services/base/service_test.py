from unittest.mock import patch
from unittest.mock import MagicMock, Mock
from pytest import raises

from mash.services.mash_service import MashService

from mash.mash_exceptions import MashRabbitConnectionException


class TestBaseService(object):
    @patch('mash.services.mash_service.get_configuration')
    @patch('mash.services.mash_service.Connection')
    def setup(
        self, mock_connection, mock_get_configuration
    ):
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

        config = Mock()
        config.get_service_names.return_value = [
            'obs', 'uploader', 'testing', 'raw_image_uploader' 'replication',
            'publisher', 'deprecation'
        ]
        mock_get_configuration.return_value = config

        self.service = MashService('obs')

        mock_get_configuration.assert_called_once_with('obs')
        self.service.log = Mock()
        mock_connection.side_effect = Exception
        with raises(MashRabbitConnectionException):
            MashService('obs')
        self.channel.reset_mock()

    def test_post_init(self):
        self.service.post_init()

    def test_consume_queue(self):
        callback = Mock()
        self.service.consume_queue(callback, queue_name='service')
        self.channel.basic.consume.assert_called_once_with(
            callback=callback, queue='obs.service'
        )

    def test_close_connection(self):
        self.connection.close.return_value = None
        self.channel.close.return_value = None
        self.service.close_connection()
        self.connection.close.assert_called_once_with()
        self.channel.close.assert_called_once_with()

    def test_unbind_queue(self):
        self.service.unbind_queue(
            'service', 'testing', '1'
        )
        self.service.channel.queue.unbind.assert_called_once_with(
            queue='testing.service', exchange='testing', routing_key='1'
        )

    def test_should_notify(self):
        result = self.service._should_notify(
            None, 'single', 'always', 'success', 'publisher'
        )
        assert result is False

        result = self.service._should_notify(
            'test@fake.com', 'single', 'always', 'success', 'publisher'
        )
        assert result is False

    def test_create_notification_content(self):
        msg = self.service._create_notification_content(
            '1', 'failed', 'always', 'deprecation', 'test_image', 3,
            'Invalid publish permissions!'
        )

        assert msg

    @patch('mash.services.mash_service.smtplib')
    def test_send_email_notification(self, mock_smtp):
        job_id = '12345678-1234-1234-1234-123456789012'
        to = 'test@fake.com'

        self.service.smtp_ssl = False
        self.service.smtp_host = 'localhost'
        self.service.smtp_port = 25
        self.service.smtp_user = to
        self.service.smtp_pass = None
        self.service.notification_subject = '[MASH] Job Status Update'

        smtp_server = MagicMock()
        mock_smtp.SMTP_SSL.return_value = smtp_server
        mock_smtp.SMTP.return_value = smtp_server

        # Send email without SSL
        self.service.send_email_notification(
            job_id, to, 'periodic', 'success', 'now', 'replication',
            'test_image', 1
        )
        assert smtp_server.send_message.call_count == 1

        self.service.smtp_ssl = True
        self.service.smtp_pass = 'super.secret'

        # Send email with SSL
        self.service.send_email_notification(
            job_id, to, 'periodic', 'failed', 'now', 'replication',
            'test_image', 1
        )
        assert smtp_server.send_message.call_count == 2

        # Send error
        self.service.service_exchange = 'testing'
        smtp_server.send_message.side_effect = Exception('Broke!')
        self.service.send_email_notification(
            job_id, to, 'single', 'success', 'now', 'testing', 'test_image', 1
        )
        self.service.log.warning.assert_called_once_with(
            'Unable to send notification email: Broke!'
        )
