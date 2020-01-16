from unittest.mock import patch, Mock

from mash.mash_exceptions import MashPublisherException
from mash.services.publisher_service import main


class TestPublisherServiceMain(object):
    @patch('mash.services.publisher_service.BaseJobFactory')
    @patch('mash.services.publisher_service.BaseConfig')
    @patch('mash.services.publisher_service.ListenerService')
    def test_publisher_main(
        self, mock_publisher_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_publisher_service.assert_called_once_with(
            service_exchange='publisher',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.publisher_service.BaseJobFactory')
    @patch('mash.services.publisher_service.BaseConfig')
    @patch('mash.services.publisher_service.ListenerService')
    @patch('sys.exit')
    def test_publisher_main_mash_error(
        self, mock_exit, mock_publisher_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config
        mock_publisher_service.side_effect = MashPublisherException('error')

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_publisher_service.assert_called_once_with(
            service_exchange='publisher',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.publisher_service.BaseConfig')
    @patch('mash.services.publisher_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_publisher_service, mock_config
    ):
        mock_publisher_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.publisher_service.BaseConfig')
    @patch('mash.services.publisher_service.ListenerService')
    @patch('sys.exit')
    def test_publisher_main_system_exit(
        self, mock_exit, mock_publisher_service, mock_config
    ):
        mock_publisher_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.publisher_service.BaseConfig')
    @patch('mash.services.publisher_service.ListenerService')
    @patch('sys.exit')
    def test_publisher_main_unexpected_error(
        self, mock_exit, mock_publisher_service, mock_config
    ):
        mock_publisher_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
