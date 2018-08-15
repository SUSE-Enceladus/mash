from unittest.mock import patch

from mash.mash_exceptions import MashTestingException
from mash.services.testing_service import main


class TestIPATestingServiceMain(object):
    @patch('mash.services.testing_service.TestingService')
    def test_main(self, mock_testing_service):
        main()
        mock_testing_service.assert_called_once_with(
            host='localhost', service_exchange='testing',
        )

    @patch('mash.services.testing_service.TestingService')
    @patch('sys.exit')
    def test_testing_main_mash_error(self, mock_exit, mock_testing_service):
        mock_testing_service.side_effect = MashTestingException('error')

        main()

        mock_testing_service.assert_called_once_with(
            host='localhost', service_exchange='testing',
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.testing_service.TestingService')
    @patch('sys.exit')
    def test_logger_main_keyboard_interrupt(
            self, mock_exit, mock_testing_service
    ):
        mock_testing_service.side_effect = KeyboardInterrupt()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.testing_service.TestingService')
    @patch('sys.exit')
    def test_testing_main_system_exit(self, mock_exit, mock_testing_service):
        mock_testing_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(mock_testing_service.side_effect)

    @patch('mash.services.testing_service.TestingService')
    @patch('sys.exit')
    def test_testing_main_unexpected_error(
        self, mock_exit, mock_testing_service
    ):
        mock_testing_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
