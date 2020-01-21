from unittest.mock import patch, Mock

from mash.mash_exceptions import MashReplicationException
from mash.services.replication_service import main


class TestReplicationServiceMain(object):
    @patch('mash.services.replication_service.BaseJobFactory')
    @patch('mash.services.replication_service.BaseConfig')
    @patch('mash.services.replication_service.ListenerService')
    def test_replication_main(self, mock_replication_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_replication_service.assert_called_once_with(
            service_exchange='replication',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.replication_service.BaseJobFactory')
    @patch('mash.services.replication_service.BaseConfig')
    @patch('mash.services.replication_service.ListenerService')
    @patch('sys.exit')
    def test_replication_main_mash_error(
        self, mock_exit, mock_replication_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config
        mock_replication_service.side_effect = MashReplicationException(
            'error'
        )

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_replication_service.assert_called_once_with(
            service_exchange='replication',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.replication_service.BaseConfig')
    @patch('mash.services.replication_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
            self, mock_exit, mock_replication_ervice, mock_config
    ):
        mock_replication_ervice.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.replication_service.BaseConfig')
    @patch('mash.services.replication_service.ListenerService')
    @patch('sys.exit')
    def test_replication_main_system_exit(
        self, mock_exit, mock_replication_service, mock_config
    ):
        mock_replication_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(
            mock_replication_service.side_effect
        )

    @patch('mash.services.replication_service.BaseConfig')
    @patch('mash.services.replication_service.ListenerService')
    @patch('sys.exit')
    def test_replication_main_unexpected_error(
        self, mock_exit, mock_replication_service, mock_config
    ):
        mock_replication_service.side_effect = Exception('Error!')
        main()
        mock_exit.assert_called_once_with(1)
