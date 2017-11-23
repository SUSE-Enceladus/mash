from mock import Mock
from mock import call
from mock import patch

from mash.services.uploader.upload_image import UploadImage


class TestUploadImage(object):
    def setup(self):
        self.connection = Mock()
        self.upload_image = UploadImage(
            self.connection, '123', 'ec2',
            'cloud_image_name', 'cloud_image_description',
            custom_uploader_args={'cloud-specific-param': 'foo'}
        )
        assert self.upload_image.channel.queue_declare.call_args_list == [
            call(durable=True, queue='credentials.ec2'),
            call(durable=True, queue='obs.listener_123')
        ]
        assert self.upload_image.channel.basic_consume.call_args_list == [
            call(
                self.upload_image._credentials_job_data,
                queue='credentials.ec2'
            ),
            call(
                self.upload_image._obs_job_data,
                queue='obs.listener_123'
            )
        ]

    @patch('mash.services.uploader.upload_image.Upload')
    def test_upload(self, mock_Upload):
        uploader = Mock()
        mock_Upload.return_value = uploader
        self.upload_image.system_image_file = 'image_file'
        self.upload_image.credentials_token = 'token'
        self.upload_image.upload(service_lookup_timeout_sec=100)
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file', 'cloud_image_name', 'cloud_image_description',
            'token', {'cloud-specific-param': 'foo'}, None
        )
        self.connection.add_timeout.assert_called_once_with(
            100, self.upload_image._consuming_timeout
        )
        self.upload_image.channel.start_consuming.assert_called_once_with()
        uploader.upload.assert_called_once_with()

    def test_obs_job_data(self):
        body = '{"image_source": ["image", "checksum"]}'
        self.upload_image._obs_job_data(Mock(), Mock(), Mock(), body)
        self.upload_image.channel.queue_delete.assert_called_once_with(
            queue='obs.listener_123'
        )
        assert self.upload_image.system_image_file == 'image'

    def test_credentials_job_data(self):
        body = '{"credentials": "abc"}'
        self.upload_image._credentials_job_data(Mock(), Mock(), Mock(), body)
        assert self.upload_image.credentials_token == 'abc'

    def test_consuming_timeout(self):
        self.upload_image._consuming_timeout()
