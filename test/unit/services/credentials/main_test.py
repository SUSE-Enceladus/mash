from unittest.mock import patch

from mash.mash_exceptions import MashException
from mash.services.credentials_service import main


class TestCredentials(object):
    @patch('mash.services.credentials_service.CredentialsService')
    def test_main(self, mock_CredentialsService):
        main()
        mock_CredentialsService.assert_called_once_with(
            service_exchange='credentials'
        )

    @patch('mash.services.credentials_service.CredentialsService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.credentials_service.CredentialsService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.credentials_service.CredentialsService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.credentials_service.CredentialsService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
