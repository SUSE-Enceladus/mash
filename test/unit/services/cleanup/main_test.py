from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.cleanup_service import main


class TestCleanup(object):
    @patch('mash.services.cleanup_service.CleanupConfig')
    @patch('mash.services.cleanup_service.CleanupService')
    def test_main(self, mock_cleanup_service, mock_config):
        config = Mock()
        mock_config.return_value = config

        main()
        mock_cleanup_service.assert_called_once_with(
            service_exchange='cleanup',
            config=config
        )

    @patch('mash.services.cleanup_service.CleanupConfig')
    @patch('mash.services.cleanup_service.CleanupService')
    @patch('sys.exit')
    def test_cleanup_main_mash_error(
        self, mock_exit, mock_cleanup_service, mock_config
    ):
        config = Mock()
        mock_config.return_value = config

        mock_cleanup_service.side_effect = MashException('error')

        main()

        mock_cleanup_service.assert_called_once_with(
            service_exchange='cleanup',
            config=config
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.cleanup_service.CleanupConfig')
    @patch('mash.services.cleanup_service.CleanupService')
    @patch('sys.exit')
    def test_cleanup_main_keyboard_interrupt(
        self, mock_exit, mock_cleanup_service, mock_config
    ):
        mock_cleanup_service.side_effect = KeyboardInterrupt()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.cleanup_service.CleanupConfig')
    @patch('mash.services.cleanup_service.CleanupService')
    @patch('sys.exit')
    def test_cleanup_main_system_exit(
        self, mock_exit, mock_cleanup_service, mock_config
    ):
        mock_cleanup_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.cleanup_service.CleanupConfig')
    @patch('mash.services.cleanup_service.CleanupService')
    @patch('sys.exit')
    def test_cleanup_main_unexpected_error(
        self, mock_exit, mock_cleanup_service, mock_config
    ):
        mock_cleanup_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
