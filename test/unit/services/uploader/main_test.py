from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.uploader_service import main


class TestUploader(object):
    @patch('mash.services.uploader_service.BaseJobFactory')
    @patch('mash.services.uploader_service.UploaderConfig')
    @patch('mash.services.uploader_service.ListenerService')
    def test_main(self, mock_UploadImageService, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_UploadImageService.assert_called_once_with(
            service_exchange='uploader',
            config=config,
            custom_args={
                'listener_msg_args': ['image_file'],
                'status_msg_args': ['source_regions', 'image_file'],
                'job_factory': factory
            }
        )

    @patch('mash.services.uploader_service.UploaderConfig')
    @patch('mash.services.uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_UploadImageService, mock_config
    ):
        mock_UploadImageService.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.uploader_service.UploaderConfig')
    @patch('mash.services.uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_UploadImageService, mock_config
    ):
        mock_UploadImageService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.uploader_service.UploaderConfig')
    @patch('mash.services.uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_UploadImageService, mock_config
    ):
        mock_UploadImageService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.uploader_service.UploaderConfig')
    @patch('mash.services.uploader_service.ListenerService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_UploadImageService, mock_config
    ):
        mock_UploadImageService.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
