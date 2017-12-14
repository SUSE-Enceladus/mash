from pytest import raises
from unittest.mock import patch
from unittest.mock import Mock

from mash.mash_exceptions import MashException
from mash.services.uploader_service import main


class TestUploader(object):
    def setup(self):
        self.config = Mock()
        self.config.get_log_file = Mock(
            return_value='/tmp/uploader_service.log'
        )

    @patch('mash.services.uploader_service.UploadImageService')
    def test_main(self, mock_UploadImageService):
        main(event_loop=False)
        mock_UploadImageService.assert_called_once_with(
            host='localhost', service_exchange='uploader'
        )

    @patch('mash.services.uploader_service.UploadImageService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_UploadImageService
    ):
        mock_UploadImageService.side_effect = MashException('error')
        main(event_loop=False)
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.uploader_service.UploadImageService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_UploadImageService
    ):
        mock_UploadImageService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.uploader_service.UploadImageService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_UploadImageService
    ):
        mock_UploadImageService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.uploader_service.UploadImageService')
    def test_main_unexpected_error(
        self, mock_UploadImageService
    ):
        mock_UploadImageService.side_effect = Exception
        with raises(Exception):
            main()
