from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.raw_image_uploader_service import main


class TestRawImageUploader(object):
    @patch('mash.services.raw_image_uploader_service.BaseConfig')
    @patch('mash.services.raw_image_uploader_service.ListenerService')
    def test_main(self, mock_RawUploadImageService, mock_config):
        config = Mock()
        mock_config.return_value = config

        main()
        mock_RawUploadImageService.assert_called_once_with(
            service_exchange='raw_image_uploader',
            config=config,
            custom_args={
                'listener_msg_args': [
                    'cloud_image_name', 'image_file', 'source_regions'
                ],
                'status_msg_args': ['source_regions']
            }
        )

    @patch('mash.services.raw_image_uploader_service.BaseConfig')
    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_RawUploadImageService, mock_config
    ):
        mock_RawUploadImageService.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.raw_image_uploader_service.BaseConfig')
    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_RawUploadImageService, mock_config
    ):
        mock_RawUploadImageService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.raw_image_uploader_service.BaseConfig')
    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_RawUploadImageService, mock_config
    ):
        mock_RawUploadImageService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.raw_image_uploader_service.BaseConfig')
    @patch('mash.services.raw_image_uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_RawUploadImageService, mock_config
    ):
        mock_RawUploadImageService.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
