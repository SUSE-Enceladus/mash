from mock import Mock
from mock import call
from mock import patch

from mash.services.uploader.upload_image import UploadImage


class MockChannel(Mock):
    vals = [True, True, True, True, True]
    tags = [[], ['tag']]
    open_count = 0
    tags_count = 0

    @property
    def is_open(self):
        val = self.vals[self.open_count]
        self.open_count += 1
        return val

    @property
    def consumer_tags(self):
        tag = self.tags[self.tags_count]
        self.tags_count += 1
        return tag


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
    @patch('mash.services.uploader.upload_image.UriConnection')
    def test_consume_service_information(
        self, mock_uri_connection, mock_consuming_timeout
    ):
        connection = Mock()
        channel = MockChannel()
        connection.channel.return_value = channel
        mock_uri_connection.return_value = connection
        self.upload_image._consume_service_information()
        mock_uri_connection.assert_called_once_with(
            'amqp://guest:guest@localhost:5672/%2F?heartbeat=600'
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
        channel.process_data_events.assert_called_once_with()
        mock_consuming_timeout.assert_called_once_with()
        channel.process_data_events.side_effect = Exception
        self.upload_image._consume_service_information()
        channel.stop_consuming.assert_called_once_with()
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with()

        self.upload_image.service_lookup_timeout_sec = None
        self.upload_image._consume_service_information()
        channel.start_consuming.assert_called_once_with()

    def test_obs_job_data(self):
        body = '{"image_source": ["image", "checksum"]}'
        channel = Mock()
        tag = Mock()
        method = {'delivery_tag': tag}
        self.upload_image._obs_job_data(body, channel, method, Mock())
        channel.basic.ack.assert_called_once_with(delivery_tag=tag)
        channel.queue.delete.assert_called_once_with(
            queue='obs.listener_123'
        )
        assert self.upload_image.system_image_file == 'image'

    def test_credentials_job_data(self):
        body = '{"credentials": "abc"}'
        channel = Mock()
        tag = Mock()
        method = {'delivery_tag': tag}
        self.upload_image._credentials_job_data(body, channel, method, Mock())
        channel.basic.ack.assert_called_once_with(delivery_tag=tag)
        channel.queue.delete.assert_called_once_with(
            queue='credentials.ec2_123'
        )
        assert self.upload_image.credentials_token == 'abc'

    def test_consuming_timeout(self):
        self.upload_image._consuming_timeout()
        assert self.upload_image.consuming_timeout_reached is True
