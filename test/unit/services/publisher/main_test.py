from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher_service import main


class TestPublisherServiceMain(object):
    @patch('mash.services.publisher_service.PublisherService')
    def test_publisher_main(self, mock_publisher_service):
        main()
        mock_publisher_service.assert_called_once_with(
            host='localhost', service_exchange='publisher',
        )

    @patch('mash.services.publisher_service.PublisherService')
    @patch('sys.exit')
    def test_publisher_main_mash_error(
        self, mock_exit, mock_publisher_service
    ):
        mock_publisher_service.side_effect = MashPublisherException('error')

        main()
        mock_publisher_service.assert_called_once_with(
            host='localhost', service_exchange='publisher',
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.publisher_service.PublisherService')
    @patch('sys.exit')
    def test_publisher_main_system_exit(
        self, mock_exit, mock_publisher_service
    ):
        mock_publisher_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.publisher_service.PublisherService')
    def test_publisher_main_unexpected_error(self, mock_publisher_service):
        mock_publisher_service.side_effect = Exception('Error!')

        with raises(Exception):
            main()
