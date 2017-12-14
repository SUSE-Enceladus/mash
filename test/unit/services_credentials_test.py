from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import MashException
from mash.services.credentials_service import main


class TestCredentials(object):
    @patch('mash.services.credentials_service.CredentialsService')
    def test_main(self, mock_CredentialsService):
        main(event_loop=False)
        mock_CredentialsService.assert_called_once_with(
            host='localhost', service_exchange='credentials'
        )

    @patch('mash.services.credentials_service.CredentialsService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = MashException('error')
        main(event_loop=False)
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
    def test_main_unexpected_error(
        self, mock_CredentialsService
    ):
        mock_CredentialsService.side_effect = Exception
        with raises(Exception):
            main()
