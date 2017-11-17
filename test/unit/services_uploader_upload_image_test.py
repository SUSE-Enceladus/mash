from mock import Mock
from mock import patch

from mash.services.uploader.upload_image import UploadImage


class TestUploadImage(object):
    @patch('mash.services.uploader.upload_image.pika.BlockingConnection')
    def setup(self, mock_BlockingConnection):
        self.connection = Mock()
        mock_BlockingConnection.return_value = self.connection
        self.upload_image = UploadImage(
            '123', 'ec2', 'cloud_image_name', 'cloud_image_description',
            'secret_token', custom_uploader_args={'cloud-specific-param': 'foo'}
        )

    @patch('mash.services.uploader.upload_image.Upload')
    def test_upload(self, mock_Upload):
        self.upload_image.system_image_file = 'image_file'
        self.upload_image.upload(obs_lookup_timeout=100)
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file', 'cloud_image_name', 'cloud_image_description',
            'secret_token', {'cloud-specific-param': 'foo'}, None
        )
        self.upload_image.channel.queue_declare.assert_called_once_with(
            durable=True, queue='obs.listener_123'
        )
        self.upload_image.channel.basic_consume.assert_called_once_with(
            self.upload_image._obs_job_data, queue='obs.listener_123'
        )
        self.connection.add_timeout.assert_called_once_with(
            100, self.upload_image._obs_job_timeout
        )
        self.upload_image.channel.start_consuming.assert_called_once_with()

    def test_obs_job_data(self):
        body = '{"image_source": ["image", "checksum"]}'
        self.upload_image._obs_job_data(Mock(), Mock(), Mock(), body)
        self.upload_image.channel.queue_delete.assert_called_once_with(
            queue='obs.listener_123'
        )
        assert self.upload_image.system_image_file == 'image'

    def test_obs_job_timeout(self):
        self.upload_image._obs_job_timeout()
        self.upload_image.channel.queue_delete.assert_called_once_with(
            queue='obs.listener_123'
        )
