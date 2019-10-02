from unittest.mock import patch
from unittest.mock import Mock

from mash.mash_exceptions import MashException
from mash.services.raw_image_uploader_service import main


class TestRawImageUploader(object):
    def setup(self):
        self.config = Mock()
        self.config.get_log_file = Mock(
            return_value='/tmp/raw_image_uploader_service.log'
        )

    @patch('mash.services.raw_image_uploader_service.ListenerService')
    def test_main(self, mock_RawUploadImageService):
        main()
        mock_RawUploadImageService.assert_called_once_with(
            custom_args={
                'listener_msg_args': ['cloud_image_name', 'image_file'],
                'status_msg_args': ['source_regions']
            },
            service_exchange='raw_image_uploader'
        )

    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_RawUploadImageService
    ):
        mock_RawUploadImageService.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_RawUploadImageService
    ):
        mock_RawUploadImageService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_RawUploadImageService
    ):
        mock_RawUploadImageService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_RawUploadImageService
    ):
        mock_RawUploadImageService.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
