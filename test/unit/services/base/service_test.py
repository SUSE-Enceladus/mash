from unittest.mock import patch
from unittest.mock import Mock
from pytest import raises

from mash.services.mash_service import MashService

from mash.mash_exceptions import MashRabbitConnectionException


class TestBaseService(object):

    @patch('mash.services.mash_service.EmailNotification')
    @patch('mash.services.mash_service.Connection')
    def setup(
        self, mock_connection, mock_email_notif
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
            'obs', 'upload', 'create', 'raw_image_upload', 'testing',
            'replication', 'publisher', 'deprecation'
        ]

        self.service = MashService('obs', config=config)

        assert mock_email_notif.call_count == 1
        self.service.log = Mock()
        mock_connection.side_effect = Exception
        with raises(MashRabbitConnectionException):
            MashService('obs', config=config)
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

        result = self.service._should_notify(
            'test@fake.com', 'periodic', 'now', 'success', 'publisher'
        )
        assert result is True

        result = self.service._should_notify(
            'test@fake.com', 'single', 'now', 'success', 'obs'
        )
        assert result is True

    def test_create_notification_content(self):
        # Failed message
        msg = self.service._create_notification_content(
            '1', 'failed', 'always', 'deprecation', 'test_image', 3,
            'Invalid publish permissions!'
        )

        assert 'Job failed' in msg

        # Job finished with success
        msg = self.service._create_notification_content(
            '1', 'success', 'now', 'obs', 'test_image', 3
        )

        assert 'Job finished successfully' in msg

        # Service with success
        msg = self.service._create_notification_content(
            '1', 'success', 'now', 'publisher', 'test_image', 3
        )

        assert 'Job finished through the obs service' in msg

    def test_send_email_notification(self):
        job_id = '12345678-1234-1234-1234-123456789012'
        to = 'test@fake.com'

        notif_class = Mock()
        self.service.notification_class = notif_class

        self.service.send_notification(
            job_id, to, 'periodic', 'failed', 'now', 'replication',
            'test_image', 1
        )
        assert notif_class.send_notification.call_count == 1
