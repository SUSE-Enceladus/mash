from unittest.mock import patch, Mock

from mash.mash_exceptions import MashReplicateException
from mash.services.replicate_service import main


class TestReplicateServiceMain(object):
    @patch('mash.services.replicate_service.BaseJobFactory')
    @patch('mash.services.replicate_service.BaseConfig')
    @patch('mash.services.replicate_service.ListenerService')
    def test_replicate_main(self, mock_replicate_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_replicate_service.assert_called_once_with(
            service_exchange='replicate',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.replicate_service.BaseJobFactory')
    @patch('mash.services.replicate_service.BaseConfig')
    @patch('mash.services.replicate_service.ListenerService')
    @patch('sys.exit')
    def test_replicate_main_mash_error(
        self, mock_exit, mock_replicate_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config
        mock_replicate_service.side_effect = MashReplicateException(
            'error'
        )

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_replicate_service.assert_called_once_with(
            service_exchange='replicate',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.replicate_service.BaseConfig')
    @patch('mash.services.replicate_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
            self, mock_exit, mock_replicate_ervice, mock_config
    ):
        mock_replicate_ervice.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.replicate_service.BaseConfig')
    @patch('mash.services.replicate_service.ListenerService')
    @patch('sys.exit')
    def test_replicate_main_system_exit(
        self, mock_exit, mock_replicate_service, mock_config
    ):
        mock_replicate_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(
            mock_replicate_service.side_effect
        )

    @patch('mash.services.replicate_service.BaseConfig')
    @patch('mash.services.replicate_service.ListenerService')
    @patch('sys.exit')
    def test_replicate_main_unexpected_error(
        self, mock_exit, mock_replicate_service, mock_config
    ):
        mock_replicate_service.side_effect = Exception('Error!')
        main()
        mock_exit.assert_called_once_with(1)
