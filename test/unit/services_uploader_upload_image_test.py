from mock import Mock
from mock import call
from mock import patch

from mash.services.uploader.upload_image import UploadImage


class TestUploadImage(object):
    @patch('mash.services.uploader.upload_image.BackgroundScheduler')
    def setup(self, mock_BackgroundScheduler):
        self.scheduler = Mock()
        self.job = Mock()
        self.scheduler.add_job.return_value = self.job
        mock_BackgroundScheduler.return_value = self.scheduler

        self.upload_image = UploadImage(
            '123', 'ec2', 'cloud_image_name', 'cloud_image_description',
            custom_uploader_args={'cloud-specific-param': 'foo'},
            service_lookup_timeout_sec=100
        )
        mock_BackgroundScheduler.assert_called_once_with()
        self.scheduler.add_job.assert_called_once_with(
            self.upload_image._consume_service_information
        )
        self.scheduler.start.assert_called_once_with()

    @patch('mash.services.uploader.upload_image.Upload')
    def test_upload(self, mock_Upload):
        uploader = Mock()
        mock_Upload.return_value = uploader
        self.upload_image.system_image_file = 'image_file'
        self.upload_image.credentials_token = 'token'
        self.upload_image.upload()
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file', 'cloud_image_name', 'cloud_image_description',
            'token', {'cloud-specific-param': 'foo'}, None
        )
        uploader.upload.assert_called_once_with()

    def test_upload_timeout_reached(self):
        self.upload_image.consuming_timeout_reached = True
        assert self.upload_image.upload() is None

    @patch('time.sleep')
    def test_upload_timeboxed(self, mock_sleep):
        def side_effect(arg):
            self.upload_image.consuming_timeout_reached = True

        mock_sleep.side_effect = side_effect
        self.upload_image.upload()
        mock_sleep.assert_called_once_with(1)

    @patch.object(UploadImage, '_consuming_timeout')
    @patch('mash.services.uploader.upload_image.Connection')
    def test_consume_service_information(
        self, mock_connection, mock_consuming_timeout
    ):
        def no_consumer_tags():
            self.upload_image.channel.consumer_tags = []

        connection = Mock()
        channel = Mock()
        channel.is_open = True
        connection.channel.return_value = channel
        mock_connection.return_value = connection
        self.upload_image.service_lookup_timeout_sec = 0.01
        self.upload_image._consume_service_information()
        mock_connection.assert_called_once_with(
            'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
        )
        assert channel.queue.declare.call_args_list == [
            call(durable=True, queue='credentials.ec2_123'),
            call(durable=True, queue='obs.listener_123')
        ]
        assert channel.basic.consume.call_args_list == [
            call(
                callback=self.upload_image._credentials_job_data,
                queue='credentials.ec2_123'
            ),
            call(
                callback=self.upload_image._obs_job_data,
                queue='obs.listener_123'
            )
        ]
        assert channel.process_data_events.called
        mock_consuming_timeout.assert_called_once_with()

        mock_consuming_timeout.reset_mock()
        channel.process_data_events.side_effect = no_consumer_tags
        self.upload_image._consume_service_information()
        assert not mock_consuming_timeout.called

        channel.stop_consuming.reset_mock()
        channel.close.reset_mock()
        connection.close.reset_mock()
        channel.process_data_events.side_effect = Exception
        self.upload_image._consume_service_information()
        channel.stop_consuming.assert_called_once_with()
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with()

        self.upload_image.service_lookup_timeout_sec = None
        self.upload_image._consume_service_information()
        channel.start_consuming.assert_called_once_with()

    def test_obs_job_data(self):
        message = Mock()
        message.body = '{"image_source": ["image", "checksum"]}'
        self.upload_image._obs_job_data(message)
        message.ack.assert_called_once_with()
        message.channel.queue.delete.assert_called_once_with(
            queue='obs.listener_123'
        )
        assert self.upload_image.system_image_file == 'image'

    def test_credentials_job_data(self):
        message = Mock()
        message.body = '{"credentials": "abc"}'
        self.upload_image._credentials_job_data(message)
        message.ack.assert_called_once_with()
        message.channel.queue.delete.assert_called_once_with(
            queue='credentials.ec2_123'
        )
        assert self.upload_image.credentials_token == 'abc'

    def test_consuming_timeout(self):
        self.upload_image._consuming_timeout()
        assert self.upload_image.consuming_timeout_reached is True
