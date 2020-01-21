from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.create_service import main


class TestCreate(object):
    @patch('mash.services.create_service.BaseJobFactory')
    @patch('mash.services.create_service.BaseConfig')
    @patch('mash.services.create_service.ListenerService')
    def test_main(self, mock_create_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_create_service.assert_called_once_with(
            service_exchange='create',
            config=config,
            custom_args={
                'listener_msg_args': ['image_file', 'source_regions'],
                'status_msg_args': ['image_file', 'source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.create_service.BaseConfig')
    @patch('mash.services.create_service.ListenerService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_create_service, mock_config
    ):
        mock_create_service.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.create_service.BaseConfig')
    @patch('mash.services.create_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_create_service, mock_config
    ):
        mock_create_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.create_service.BaseConfig')
    @patch('mash.services.create_service.ListenerService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_create_service, mock_config
    ):
        mock_create_service.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.create_service.BaseConfig')
    @patch('mash.services.create_service.ListenerService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_create_service, mock_config
    ):
        mock_create_service.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
