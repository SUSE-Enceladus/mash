import datetime

from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from mash.services.uploader.upload_image import UploadImage


class TestUploadImage(object):
    @patch('distutils.dir_util.mkpath')
    def setup(self, mock_mkpath):
        self.custom_uploader_args = {'cloud-specific-param': 'foo'}
        self.upload_image = UploadImage(
            '123', 'job_file', 'ec2',
            'token', 'cloud_image_name_at_{date}',
            'cloud_image_description',
            last_upload_region=False,
            custom_uploader_args=self.custom_uploader_args
        )
        self.upload_image.set_image_file('image_file')

    @patch('mash.services.uploader.upload_image.Upload')
    @patch.object(UploadImage, '_log_callback')
    @patch.object(UploadImage, '_result_callback')
    def test_upload(
        self, mock_result_callback, mock_log_callback, mock_Upload
    ):
        today = datetime.date.today()
        uploader = Mock()
        uploader.upload.return_value = ('image_id', 'region')
        mock_Upload.return_value = uploader
        self.upload_image.upload()
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file',
            'cloud_image_name_at_{0}'.format(today.strftime("%Y%m%d")),
            'cloud_image_description',
            'token', {'cloud-specific-param': 'foo'}
        )
        uploader.upload.assert_called_once_with()
        assert mock_log_callback.call_args_list == [
            call(
                'Uploading image to ec2: image_file:{0}'.format(
                    self.custom_uploader_args
                )
            ),
            call('Uploaded image has ID: image_id')
        ]
        mock_result_callback.assert_called_once_with()

        mock_log_callback.reset_mock()
        uploader.upload.side_effect = Exception('error')
        self.upload_image.upload()
        assert mock_log_callback.call_args_list == [
            call(
                'Uploading image to ec2: image_file:{0}'.format(
                    self.custom_uploader_args
                )
            ),
            call('error')
        ]

    @patch('mash.services.uploader.upload_image.Upload')
    @patch.object(UploadImage, '_log_callback')
    @patch.object(UploadImage, '_result_callback')
    def test_upload_cloud_image_name_convention_error(
        self, mock_result_callback, mock_log_callback, mock_Upload
    ):
        self.upload_image.cloud_image_name = 'name_with_no_date_key'
        self.upload_image.upload()
        assert mock_log_callback.call_args_list[1] == call(
            'No {date} key specified in cloud_image_name format: '
            'name_with_no_date_key'
        )

        mock_log_callback.reset_mock()

        self.upload_image.cloud_image_name = 'name_with_{invalid}_format'
        self.upload_image.upload()
        assert mock_log_callback.call_args_list[1] == call(
            'Invalid cloud_image_name format to apply {date} in: '
            'name_with_{invalid}_format'
        )

    def test_set_log_handler(self):
        function = Mock()
        self.upload_image.set_log_handler(function)
        assert self.upload_image.log_callback == function

    def test_set_result_handler(self):
        function = Mock()
        self.upload_image.set_result_handler(function)
        assert self.upload_image.result_callback == function

    @patch.object(UploadImage, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.upload_image.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_log_callback(self):
        self.upload_image.log_callback = Mock()
        self.upload_image.iteration_count = 1
        self.upload_image._log_callback('message')
        self.upload_image.log_callback.assert_called_once_with(
            '123', 'Pass[1]: message'
        )

    def test_result_callback(self):
        self.upload_image.result_callback = Mock()
        self.upload_image.cloud_image_id = 'id'
        self.upload_image._result_callback()
        self.upload_image.result_callback.assert_called_once_with(
            '123', False, {
                'cloud_image_id': 'id',
                'upload_region': None,
                'csp_name': 'ec2',
                'job_status': 'success'
            }
        )
        self.upload_image.result_callback.reset_mock()
        self.upload_image.cloud_image_id = None
        self.upload_image.upload_region = 'eu-central-1'
        self.upload_image._result_callback()
        self.upload_image.result_callback.assert_called_once_with(
            '123', False, {
                'cloud_image_id': None,
                'upload_region': 'eu-central-1',
                'csp_name': 'ec2',
                'job_status': 'failed'
            }
        )
