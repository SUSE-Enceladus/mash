from unittest.mock import patch, Mock

from mash.mash_exceptions import MashDeprecateException
from mash.services.deprecate_service import main


class TestDeprecateServiceMain(object):
    @patch('mash.services.deprecate_service.BaseJobFactory')
    @patch('mash.services.deprecate_service.BaseConfig')
    @patch('mash.services.deprecate_service.ListenerService')
    def test_main(self, mock_deprecate_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_deprecate_service.assert_called_once_with(
            service_exchange='deprecate',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.deprecate_service.BaseJobFactory')
    @patch('mash.services.deprecate_service.BaseConfig')
    @patch('mash.services.deprecate_service.ListenerService')
    @patch('sys.exit')
    def test_deprecate_main_mash_error(
        self, mock_exit, mock_deprecate_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        mock_deprecate_service.side_effect = MashDeprecateException(
            'error'
        )

        main()

        mock_deprecate_service.assert_called_once_with(
            service_exchange='deprecate',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.deprecate_service.BaseConfig')
    @patch('mash.services.deprecate_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_deprecate_service, mock_config
    ):
        mock_deprecate_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.deprecate_service.BaseConfig')
    @patch('mash.services.deprecate_service.ListenerService')
    @patch('sys.exit')
    def test_deprecate_main_system_exit(
        self, mock_exit, mock_deprecate_service, mock_config
    ):
        mock_deprecate_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(mock_deprecate_service.side_effect)

    @patch('mash.services.deprecate_service.BaseConfig')
    @patch('mash.services.deprecate_service.ListenerService')
    @patch('sys.exit')
    def test_deprecate_main_unexpected_error(
        self, mock_exit, mock_deprecate_service, mock_config
    ):
        mock_deprecate_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
