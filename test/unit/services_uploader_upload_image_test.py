from pytest import raises
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from .test_helper import (
    patch_open,
    context_manager
)

from mash.services.uploader.upload_image import UploadImage
from mash.mash_exceptions import (
    MashJobRetireException
)


class TestUploadImage(object):
    @patch('mash.services.uploader.upload_image.BackgroundScheduler')
    @patch('distutils.dir_util.mkpath')
    def setup(self, mock_mkpath, mock_BackgroundScheduler):
        self.scheduler = Mock()
        self.job = Mock()
        self.scheduler.add_job.return_value = self.job
        mock_BackgroundScheduler.return_value = self.scheduler

        self.upload_image = UploadImage(
            '123', 'job_file', 'ec2',
            'cloud_image_name', 'cloud_image_description',
            custom_uploader_args={'cloud-specific-param': 'foo'},
            service_lookup_timeout_sec=100
        )
        mock_BackgroundScheduler.assert_called_once_with()
        self.scheduler.add_job.assert_called_once_with(
            self.upload_image._consume_service_information
        )
        self.scheduler.start.assert_called_once_with()

    @patch('time.sleep')
    @patch('mash.services.uploader.upload_image.Upload')
    @patch.object(UploadImage, '_log_callback')
    @patch.object(UploadImage, '_set_listen_request_for_obs_image')
    @patch.object(UploadImage, '_retire')
    @patch.object(UploadImage, '_result_callback')
    @patch.object(UploadImage, '_close_connection')
    def test_upload_oneshot(
        self, mock_close_connection, mock_result_callback, mock_retire,
        mock_set_listen_request_for_obs_image, mock_log_callback,
        mock_Upload, mock_sleep
    ):
        uploader = Mock()
        mock_Upload.return_value = uploader
        self.upload_image.system_image_file = 'image_file'
        self.upload_image.credentials_token = 'token'
        self.upload_image.upload()
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file', 'cloud_image_name', 'cloud_image_description',
            'token', {'cloud-specific-param': 'foo'}, None
        )
        mock_set_listen_request_for_obs_image.assert_called_once_with()
        uploader.upload.assert_called_once_with()
        mock_retire.assert_called_once_with()
        mock_result_callback.assert_called_once_with()
        mock_close_connection.assert_called_once_with()

        mock_log_callback.reset_mock()
        uploader.upload.side_effect = Exception('error')
        self.upload_image.image_file_uploaded = None
        self.upload_image.upload()
        assert mock_log_callback.call_args_list == [
            call('Waiting for image and credentials data'),
            call('Got image file: image_file'),
            call('Got credentials data'),
            call('Uploading image to ec2: image_file'),
            call('error')
        ]

    @patch('time.sleep')
    @patch('mash.services.uploader.upload_image.Upload')
    @patch.object(UploadImage, '_set_listen_request_for_obs_image')
    @patch.object(UploadImage, '_retire')
    @patch.object(UploadImage, '_result_callback')
    @patch.object(UploadImage, '_close_connection')
    def test_upload_always(
        self, mock_close_connection, mock_result_callback, mock_retire,
        mock_set_listen_request_for_obs_image, mock_Upload,
        mock_sleep
    ):
        def stop(sec):
            self.upload_image.consuming_timeout_reached = True

        mock_sleep.side_effect = stop

        uploader = Mock()
        mock_Upload.return_value = uploader
        self.upload_image.system_image_file = 'image_file'
        self.upload_image.credentials_token = 'token'
        self.upload_image.upload(oneshot=False)
        mock_Upload.assert_called_once_with(
            'ec2', 'image_file', 'cloud_image_name', 'cloud_image_description',
            'token', {'cloud-specific-param': 'foo'}, None
        )
        assert mock_set_listen_request_for_obs_image.call_args_list == [
            call(), call()
        ]
        uploader.upload.assert_called_once_with()
        mock_result_callback.assert_called_once_with()
        assert not mock_retire.called
        assert not mock_close_connection.called

    @patch.object(UploadImage, '_set_listen_request_for_obs_image')
    def test_upload_timeout_reached(
        self, mock_set_listen_request_for_obs_image
    ):
        self.upload_image.consuming_timeout_reached = True
        assert self.upload_image.upload() is None

    @patch('time.sleep')
    @patch.object(UploadImage, '_set_listen_request_for_obs_image')
    def test_upload_timeboxed(
        self, mock_set_listen_request_for_obs_image, mock_sleep
    ):
        def side_effect(arg):
            self.upload_image.consuming_timeout_reached = True

        mock_sleep.side_effect = side_effect
        assert self.upload_image.upload() is None
        mock_sleep.assert_called_once_with(1)

    @patch('mash.services.uploader.upload_image.Connection')
    def test_set_listen_request_for_obs_image(self, mock_connection):
        channel = Mock()
        connection = Mock()
        connection.channel.return_value = channel
        mock_connection.return_value = connection
        self.upload_image._set_listen_request_for_obs_image()
        mock_connection.assert_called_once_with(
            'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
        )
        channel.queue.declare.assert_called_once_with(
            durable=True, queue='obs.service_event'
        )
        channel.basic.publish.assert_called_once_with(
            '{"obsjob_listen": "123"}', 'service_event', 'obs', mandatory=True
        )
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    @patch('mash.services.uploader.upload_image.pickle.dump')
    @patch('os.remove')
    @patch_open
    def test_retire(
        self, mock_open, mock_os_remove, mock_pickle_dump
    ):
        context = context_manager()
        mock_open.return_value = context.context_manager_mock
        self.upload_image._retire()
        mock_os_remove.assert_called_once_with('job_file')
        mock_open.assert_called_once_with(
            '/var/tmp/mash/uploader_jobs_done//123.pickle', 'wb'
        )

    @patch('os.remove')
    def test_retire_job_file_removal_error(self, mock_os_remove):
        mock_os_remove.side_effect = Exception
        with raises(MashJobRetireException):
            self.upload_image._retire()

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
            '123', {'cloud_image_id': 'id', 'csp_name': 'ec2'}
        )

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
                callback=self.upload_image._service_data,
                queue='credentials.ec2_123'
            ),
            call(
                callback=self.upload_image._service_data,
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

    def test_service_data(self):
        message = Mock()
        message.body = '{"image_source": ["image", "checksum"]}'
        self.upload_image._service_data(message)
        message.ack.assert_called_once_with()
        assert self.upload_image.system_image_file == 'image'
        message.reset_mock()
        message.body = '{"credentials": "abc"}'
        self.upload_image._service_data(message)
        message.ack.assert_called_once_with()
        assert self.upload_image.credentials_token == 'abc'

    def test_consuming_timeout(self):
        self.upload_image._consuming_timeout()
        assert self.upload_image.consuming_timeout_reached is True

    @patch.object(UploadImage, '_consuming_timeout')
    def test_stop(self, mock_consuming_timeout):
        self.upload_image.uploader = Mock()
        self.upload_image.stop()
        mock_consuming_timeout.assert_called_once_with()
