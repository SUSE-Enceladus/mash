from unittest.mock import patch, Mock

from mash.mash_exceptions import MashPublishException
from mash.services.publish_service import main


class TestPublishServiceMain(object):
    @patch('mash.services.publish_service.BaseJobFactory')
    @patch('mash.services.publish_service.BaseConfig')
    @patch('mash.services.publish_service.ListenerService')
    def test_publish_main(
        self, mock_publish_service, mock_config, mock_factory
    ):
        config = Mock()
        config.get_publish_thread_pool_count.return_value = 50
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_publish_service.assert_called_once_with(
            service_exchange='publish',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory,
                'thread_pool_count': 50
            }
        )

    @patch('mash.services.publish_service.BaseJobFactory')
    @patch('mash.services.publish_service.BaseConfig')
    @patch('mash.services.publish_service.ListenerService')
    @patch('sys.exit')
    def test_publish_main_mash_error(
        self, mock_exit, mock_publish_service, mock_config, mock_factory
    ):
        config = Mock()
        config.get_publish_thread_pool_count.return_value = 50
        mock_config.return_value = config
        mock_publish_service.side_effect = MashPublishException('error')

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_publish_service.assert_called_once_with(
            service_exchange='publish',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory,
                'thread_pool_count': 50
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.publish_service.BaseConfig')
    @patch('mash.services.publish_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_publish_service, mock_config
    ):
        mock_publish_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.publish_service.BaseConfig')
    @patch('mash.services.publish_service.ListenerService')
    @patch('sys.exit')
    def test_publish_main_system_exit(
        self, mock_exit, mock_publish_service, mock_config
    ):
        mock_publish_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.publish_service.BaseConfig')
    @patch('mash.services.publish_service.ListenerService')
    @patch('sys.exit')
    def test_publish_main_unexpected_error(
        self, mock_exit, mock_publish_service, mock_config
    ):
        mock_publish_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
